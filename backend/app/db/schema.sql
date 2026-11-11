-- GymFlow PostgreSQL schema reference
--
-- This file documents the existing application schema for development.
-- It is NOT an Alembic migration and must NOT be executed against Neon.
-- Neon roles, grants, and the Alembic version table are intentionally excluded.

CREATE TYPE "user_role" AS ENUM('client', 'trainer', 'admin');
CREATE TYPE "membership_status" AS ENUM('active', 'expired', 'cancelled');
CREATE TYPE "payment_status" AS ENUM('pending', 'paid', 'failed', 'refunded');
CREATE TYPE "payment_method" AS ENUM('card', 'cash', 'transfer', 'simulated');
CREATE TYPE "booking_status" AS ENUM('confirmed', 'waitlist', 'cancelled', 'attended', 'no_show');
CREATE TYPE "checkin_method" AS ENUM('qr', 'manual', 'card');

CREATE TABLE "bookings" (
	"id" bigserial PRIMARY KEY,
	"session_id" bigint NOT NULL,
	"user_id" bigint NOT NULL,
	"status" booking_status DEFAULT 'confirmed' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"cancelled_at" timestamp with time zone,
	CONSTRAINT "ux_booking_session_user" UNIQUE("session_id","user_id")
);
CREATE TABLE "check_ins" (
	"id" bigserial PRIMARY KEY,
	"user_id" bigint NOT NULL,
	"membership_id" bigint,
	"checked_in_at" timestamp with time zone DEFAULT now() NOT NULL,
	"checked_out_at" timestamp with time zone,
	"method" checkin_method DEFAULT 'manual' NOT NULL,
	CONSTRAINT "ck_checkout_after_checkin" CHECK (((checked_out_at IS NULL) OR (checked_out_at >= checked_in_at)))
);
CREATE TABLE "class_sessions" (
	"id" bigserial PRIMARY KEY,
	"class_type_id" bigint NOT NULL,
	"trainer_id" bigint NOT NULL,
	"starts_at" timestamp with time zone NOT NULL,
	"ends_at" timestamp with time zone NOT NULL,
	"capacity" integer NOT NULL,
	"room" varchar(50),
	"is_cancelled" boolean DEFAULT false NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "ck_session_capacity" CHECK ((capacity > 0)),
	CONSTRAINT "ck_session_time" CHECK ((ends_at > starts_at))
);
CREATE TABLE "class_types" (
	"id" bigserial PRIMARY KEY,
	"name" varchar(100) NOT NULL CONSTRAINT "class_types_name_key" UNIQUE,
	"description" text,
	"duration_minutes" integer NOT NULL,
	"default_capacity" integer NOT NULL,
	CONSTRAINT "ck_class_types_capacity" CHECK ((default_capacity > 0)),
	CONSTRAINT "ck_class_types_duration" CHECK ((duration_minutes > 0))
);
CREATE TABLE "membership_types" (
	"id" bigserial PRIMARY KEY,
	"name" varchar(100) NOT NULL CONSTRAINT "membership_types_name_key" UNIQUE,
	"description" text,
	"duration_days" integer NOT NULL,
	"price" numeric(10, 2) NOT NULL,
	"max_entries" integer,
	"is_active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "ck_membership_types_duration" CHECK ((duration_days > 0)),
	CONSTRAINT "ck_membership_types_entries" CHECK (((max_entries IS NULL) OR (max_entries > 0))),
	CONSTRAINT "ck_membership_types_price" CHECK ((price >= (0)::numeric))
);
CREATE TABLE "memberships" (
	"id" bigserial PRIMARY KEY,
	"user_id" bigint NOT NULL,
	"membership_type_id" bigint NOT NULL,
	"start_date" date NOT NULL,
	"end_date" date NOT NULL,
	"status" membership_status DEFAULT 'active' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "ck_membership_dates" CHECK ((end_date >= start_date))
);
CREATE TABLE "payments" (
	"id" bigserial PRIMARY KEY,
	"user_id" bigint NOT NULL,
	"membership_id" bigint,
	"amount" numeric(10, 2) NOT NULL,
	"currency" varchar(3) DEFAULT 'PLN' NOT NULL,
	"status" payment_status DEFAULT 'pending' NOT NULL,
	"method" payment_method DEFAULT 'simulated' NOT NULL,
	"paid_at" timestamp with time zone,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "ck_payments_amount" CHECK ((amount >= (0)::numeric))
);
CREATE TABLE "users" (
  "id"            bigserial PRIMARY KEY,
  "email"         varchar(255)                              NOT NULL,
  "password_hash" varchar(255)                              NOT NULL,
  "first_name"    varchar(100)                              NOT NULL,
  "last_name"     varchar(100)                              NOT NULL,
  "phone"         varchar(30),
  "birth_date"    date,
  "role"          user_role                DEFAULT 'client' NOT NULL,
  "is_active"     boolean                  DEFAULT true     NOT NULL,
  "created_at"    timestamp with time zone DEFAULT now()    NOT NULL,
  "updated_at"    timestamp with time zone DEFAULT now()    NOT NULL
);

CREATE UNIQUE INDEX "bookings_pkey" ON "bookings" ("id");
CREATE INDEX "ix_bookings_session" ON "bookings" ("session_id","status");
CREATE INDEX "ix_bookings_user_id" ON "bookings" ("user_id");
CREATE UNIQUE INDEX "ux_booking_session_user" ON "bookings" ("session_id","user_id");
CREATE UNIQUE INDEX "check_ins_pkey" ON "check_ins" ("id");
CREATE INDEX "ix_check_ins_checked_in_at" ON "check_ins" ("checked_in_at");
CREATE INDEX "ix_check_ins_user_time" ON "check_ins" ("user_id","checked_in_at");
CREATE UNIQUE INDEX "class_sessions_pkey" ON "class_sessions" ("id");
CREATE INDEX "ix_class_sessions_starts_at" ON "class_sessions" ("starts_at");
CREATE INDEX "ix_class_sessions_trainer" ON "class_sessions" ("trainer_id","starts_at");
CREATE UNIQUE INDEX "class_types_name_key" ON "class_types" ("name");
CREATE UNIQUE INDEX "class_types_pkey" ON "class_types" ("id");
CREATE UNIQUE INDEX "membership_types_name_key" ON "membership_types" ("name");
CREATE UNIQUE INDEX "membership_types_pkey" ON "membership_types" ("id");
CREATE INDEX "ix_memberships_status_end" ON "memberships" ("status","end_date");
CREATE INDEX "ix_memberships_user_id" ON "memberships" ("user_id");
CREATE UNIQUE INDEX "memberships_pkey" ON "memberships" ("id");
CREATE INDEX "ix_payments_paid_at" ON "payments" ("paid_at");
CREATE INDEX "ix_payments_user_id" ON "payments" ("user_id");
CREATE UNIQUE INDEX "payments_pkey" ON "payments" ("id");
CREATE INDEX "ix_users_role" ON "users" ("role");
CREATE UNIQUE INDEX "users_pkey" ON "users" ("id");
CREATE UNIQUE INDEX "ux_users_email_lower" ON "users" ("lower((email)::text)");

ALTER TABLE "bookings" ADD CONSTRAINT "bookings_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "class_sessions"("id") ON DELETE CASCADE;
ALTER TABLE "bookings" ADD CONSTRAINT "bookings_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE;
ALTER TABLE "check_ins" ADD CONSTRAINT "check_ins_membership_id_fkey" FOREIGN KEY ("membership_id") REFERENCES "memberships"("id") ON DELETE SET NULL;
ALTER TABLE "check_ins" ADD CONSTRAINT "check_ins_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE;
ALTER TABLE "class_sessions" ADD CONSTRAINT "class_sessions_class_type_id_fkey" FOREIGN KEY ("class_type_id") REFERENCES "class_types"("id");
ALTER TABLE "class_sessions" ADD CONSTRAINT "class_sessions_trainer_id_fkey" FOREIGN KEY ("trainer_id") REFERENCES "users"("id");
ALTER TABLE "memberships" ADD CONSTRAINT "memberships_membership_type_id_fkey" FOREIGN KEY ("membership_type_id") REFERENCES "membership_types"("id");
ALTER TABLE "memberships" ADD CONSTRAINT "memberships_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE;
ALTER TABLE "payments" ADD CONSTRAINT "payments_membership_id_fkey" FOREIGN KEY ("membership_id") REFERENCES "memberships"("id") ON DELETE SET NULL;
ALTER TABLE "payments" ADD CONSTRAINT "payments_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id");
