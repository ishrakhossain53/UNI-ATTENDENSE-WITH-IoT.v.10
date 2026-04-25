-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table (all roles: admin, faculty, student)
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'faculty', 'student')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Students table
CREATE TABLE students (
    student_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    student_number VARCHAR(20) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    department VARCHAR(100),
    semester INTEGER,
    fp_enrolled BOOLEAN DEFAULT FALSE,
    fp_enrolled_at TIMESTAMPTZ,
    fp_enrolled_by UUID REFERENCES users(user_id),
    is_active BOOLEAN DEFAULT TRUE
);

-- Fingerprint templates (encrypted with AES-256)
CREATE TABLE fingerprint_templates (
    template_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(student_id),
    template_data BYTEA NOT NULL,
    template_hash VARCHAR(64) NOT NULL,
    device_slot INTEGER NOT NULL,
    enrolled_by UUID REFERENCES users(user_id) ON DELETE SET NULL,
    enrolled_at TIMESTAMPTZ DEFAULT NOW(),
    sync_version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE
);

-- Add unique constraint on device_slot for active templates
CREATE UNIQUE INDEX unique_active_device_slot ON fingerprint_templates (device_slot) WHERE is_active = TRUE;

-- Device sync log
CREATE TABLE device_sync_log (
    sync_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id VARCHAR(50) NOT NULL,
    template_id UUID REFERENCES fingerprint_templates(template_id),
    sync_version INTEGER NOT NULL,
    sync_status VARCHAR(20) DEFAULT 'pending' CHECK (sync_status IN ('pending', 'sent', 'synced', 'failed')),
    synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Classrooms
CREATE TABLE classrooms (
    classroom_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_number VARCHAR(20) UNIQUE NOT NULL,
    building VARCHAR(100),
    capacity INTEGER,
    device_id VARCHAR(50)
);

-- Courses
CREATE TABLE courses (
    course_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_code VARCHAR(20) UNIQUE NOT NULL,
    course_name VARCHAR(100) NOT NULL,
    faculty_id UUID REFERENCES users(user_id),
    semester VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE
);

-- Course enrollments (students <-> courses)
CREATE TABLE course_enrollments (
    enrollment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID REFERENCES courses(course_id),
    student_id UUID REFERENCES students(student_id),
    enrolled_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(course_id, student_id)
);

-- Class schedule
CREATE TABLE class_schedule (
    schedule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID REFERENCES courses(course_id),
    classroom_id UUID REFERENCES classrooms(classroom_id),
    day_of_week VARCHAR(10) CHECK (day_of_week IN ('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday')),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL
);

-- Attendance records (partitioned by month on timestamp)
CREATE TABLE attendance_records (
    record_id UUID DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(student_id),
    classroom_id UUID NOT NULL REFERENCES classrooms(classroom_id),
    device_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    match_score INTEGER,
    battery_pct INTEGER,
    status VARCHAR(20) DEFAULT 'present' CHECK (status IN ('present', 'absent', 'manual')),
    verification_method VARCHAR(20) DEFAULT 'fingerprint',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (record_id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions for 2024-01 through 2025-12
CREATE TABLE attendance_records_2024_01 PARTITION OF attendance_records
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE attendance_records_2024_02 PARTITION OF attendance_records
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
CREATE TABLE attendance_records_2024_03 PARTITION OF attendance_records
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');
CREATE TABLE attendance_records_2024_04 PARTITION OF attendance_records
    FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');
CREATE TABLE attendance_records_2024_05 PARTITION OF attendance_records
    FOR VALUES FROM ('2024-05-01') TO ('2024-06-01');
CREATE TABLE attendance_records_2024_06 PARTITION OF attendance_records
    FOR VALUES FROM ('2024-06-01') TO ('2024-07-01');
CREATE TABLE attendance_records_2024_07 PARTITION OF attendance_records
    FOR VALUES FROM ('2024-07-01') TO ('2024-08-01');
CREATE TABLE attendance_records_2024_08 PARTITION OF attendance_records
    FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');
CREATE TABLE attendance_records_2024_09 PARTITION OF attendance_records
    FOR VALUES FROM ('2024-09-01') TO ('2024-10-01');
CREATE TABLE attendance_records_2024_10 PARTITION OF attendance_records
    FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');
CREATE TABLE attendance_records_2024_11 PARTITION OF attendance_records
    FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
CREATE TABLE attendance_records_2024_12 PARTITION OF attendance_records
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');
CREATE TABLE attendance_records_2025_01 PARTITION OF attendance_records
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE attendance_records_2025_02 PARTITION OF attendance_records
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE attendance_records_2025_03 PARTITION OF attendance_records
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE attendance_records_2025_04 PARTITION OF attendance_records
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
CREATE TABLE attendance_records_2025_05 PARTITION OF attendance_records
    FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');
CREATE TABLE attendance_records_2025_06 PARTITION OF attendance_records
    FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');
CREATE TABLE attendance_records_2025_07 PARTITION OF attendance_records
    FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');
CREATE TABLE attendance_records_2025_08 PARTITION OF attendance_records
    FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');
CREATE TABLE attendance_records_2025_09 PARTITION OF attendance_records
    FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');
CREATE TABLE attendance_records_2025_10 PARTITION OF attendance_records
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
CREATE TABLE attendance_records_2025_11 PARTITION OF attendance_records
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
CREATE TABLE attendance_records_2025_12 PARTITION OF attendance_records
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');
CREATE TABLE attendance_records_2026_01 PARTITION OF attendance_records
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE attendance_records_2026_02 PARTITION OF attendance_records
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE attendance_records_2026_03 PARTITION OF attendance_records
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE attendance_records_2026_04 PARTITION OF attendance_records
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE attendance_records_2026_05 PARTITION OF attendance_records
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE attendance_records_2026_06 PARTITION OF attendance_records
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
CREATE TABLE attendance_records_2026_07 PARTITION OF attendance_records
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
CREATE TABLE attendance_records_2026_08 PARTITION OF attendance_records
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
CREATE TABLE attendance_records_2026_09 PARTITION OF attendance_records
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
CREATE TABLE attendance_records_2026_10 PARTITION OF attendance_records
    FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
CREATE TABLE attendance_records_2026_11 PARTITION OF attendance_records
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE attendance_records_2026_12 PARTITION OF attendance_records
    FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');
CREATE TABLE attendance_records_2027_01 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-01-01') TO ('2027-02-01');
CREATE TABLE attendance_records_2027_02 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-02-01') TO ('2027-03-01');
CREATE TABLE attendance_records_2027_03 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-03-01') TO ('2027-04-01');
CREATE TABLE attendance_records_2027_04 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-04-01') TO ('2027-05-01');
CREATE TABLE attendance_records_2027_05 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-05-01') TO ('2027-06-01');
CREATE TABLE attendance_records_2027_06 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-06-01') TO ('2027-07-01');
CREATE TABLE attendance_records_2027_07 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-07-01') TO ('2027-08-01');
CREATE TABLE attendance_records_2027_08 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-08-01') TO ('2027-09-01');
CREATE TABLE attendance_records_2027_09 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-09-01') TO ('2027-10-01');
CREATE TABLE attendance_records_2027_10 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-10-01') TO ('2027-11-01');
CREATE TABLE attendance_records_2027_11 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-11-01') TO ('2027-12-01');
CREATE TABLE attendance_records_2027_12 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-12-01') TO ('2028-01-01');

-- Audit log
CREATE TABLE audit_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    ip_address INET,
    user_agent TEXT,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Gateway offline queue (temporary)
CREATE TABLE gateway_queue (
    queue_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id VARCHAR(50) NOT NULL,
    payload_encrypted TEXT NOT NULL,
    queued_at TIMESTAMPTZ DEFAULT NOW(),
    sync_status VARCHAR(20) DEFAULT 'pending' CHECK (sync_status IN ('pending', 'synced', 'failed'))
);

-- Indexes for performance
CREATE INDEX idx_attendance_student ON attendance_records(student_id);
CREATE INDEX idx_attendance_classroom ON attendance_records(classroom_id);
CREATE INDEX idx_attendance_timestamp ON attendance_records(timestamp DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_device_sync_log_device_template ON device_sync_log(device_id, template_id);
CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_created ON audit_log(created_at DESC);
CREATE INDEX idx_templates_student ON fingerprint_templates(student_id);
CREATE INDEX idx_sync_log_device ON device_sync_log(device_id);
CREATE INDEX idx_students_user ON students(user_id);
CREATE INDEX idx_courses_faculty ON courses(faculty_id);

-- SEED DATA

-- 1. Create admin user (password: admin123, bcrypted)
INSERT INTO users (username, email, password_hash, role, is_active)
VALUES (
    'admin',
    'admin@university.edu',
    '$2b$12$JejOGRI4NE1lHTJMrVG0BOTyUP9YzxWnXoQ9gA2B1kxR5WYZCb4L2',
    'admin',
    TRUE
);

-- 2. Create faculty users (password: pass123, bcrypted)
INSERT INTO users (username, email, password_hash, role, is_active)
VALUES 
    ('faculty1', 'faculty1@university.edu', '$2b$12$Tkls9uKpr8VExqgxIEmW3OoEUP6fQI3MxXM0BACCaYhJEF0TVIdKq', 'faculty', TRUE),
    ('faculty2', 'faculty2@university.edu', '$2b$12$Tkls9uKpr8VExqgxIEmW3OoEUP6fQI3MxXM0BACCaYhJEF0TVIdKq', 'faculty', TRUE);

-- 3. Create student users (password: pass123, bcrypted)
INSERT INTO users (username, email, password_hash, role, is_active)
VALUES 
    ('student01', 'student01@university.edu', '$2b$12$Tkls9uKpr8VExqgxIEmW3OoEUP6fQI3MxXM0BACCaYhJEF0TVIdKq', 'student', TRUE),
    ('student02', 'student02@university.edu', '$2b$12$Tkls9uKpr8VExqgxIEmW3OoEUP6fQI3MxXM0BACCaYhJEF0TVIdKq', 'student', TRUE),
    ('student03', 'student03@university.edu', '$2b$12$Tkls9uKpr8VExqgxIEmW3OoEUP6fQI3MxXM0BACCaYhJEF0TVIdKq', 'student', TRUE),
    ('student04', 'student04@university.edu', '$2b$12$Tkls9uKpr8VExqgxIEmW3OoEUP6fQI3MxXM0BACCaYhJEF0TVIdKq', 'student', TRUE),
    ('student05', 'student05@university.edu', '$2b$12$Tkls9uKpr8VExqgxIEmW3OoEUP6fQI3MxXM0BACCaYhJEF0TVIdKq', 'student', TRUE),
    ('student06', 'student06@university.edu', '$2b$12$Tkls9uKpr8VExqgxIEmW3OoEUP6fQI3MxXM0BACCaYhJEF0TVIdKq', 'student', TRUE),
    ('student07', 'student07@university.edu', '$2b$12$Tkls9uKpr8VExqgxIEmW3OoEUP6fQI3MxXM0BACCaYhJEF0TVIdKq', 'student', TRUE),
    ('student08', 'student08@university.edu', '$2b$12$Tkls9uKpr8VExqgxIEmW3OoEUP6fQI3MxXM0BACCaYhJEF0TVIdKq', 'student', TRUE),
    ('student09', 'student09@university.edu', '$2b$12$Tkls9uKpr8VExqgxIEmW3OoEUP6fQI3MxXM0BACCaYhJEF0TVIdKq', 'student', TRUE),
    ('student10', 'student10@university.edu', '$2b$12$Tkls9uKpr8VExqgxIEmW3OoEUP6fQI3MxXM0BACCaYhJEF0TVIdKq', 'student', TRUE);

-- 4. Create classrooms with device assignments
INSERT INTO classrooms (room_number, building, capacity, device_id)
VALUES 
    ('101', 'A', 30, 'ESP32_CLASSROOM_101'),
    ('102', 'A', 35, 'ESP32_CLASSROOM_102'),
    ('103', 'B', 40, 'ESP32_CLASSROOM_103');

-- 5. Create courses (faculty1 has 2, faculty2 has 1)
INSERT INTO courses (course_code, course_name, faculty_id, semester, is_active)
SELECT 'SE101', 'Software Engineering', user_id, '2024-Spring', TRUE FROM users WHERE username = 'faculty1'
UNION ALL
SELECT 'DB101', 'Database Design', user_id, '2024-Spring', TRUE FROM users WHERE username = 'faculty1'
UNION ALL
SELECT 'AI101', 'Artificial Intelligence', user_id, '2024-Spring', TRUE FROM users WHERE username = 'faculty2';

-- 6. Create student records linked to users
INSERT INTO students (user_id, student_number, full_name, department, semester, is_active)
SELECT user_id, 'STU001', 'Alice Rahman', 'Computer Science', 3, TRUE FROM users WHERE username = 'student01'
UNION ALL
SELECT user_id, 'STU002', 'Bob Chen', 'Computer Science', 3, TRUE FROM users WHERE username = 'student02'
UNION ALL
SELECT user_id, 'STU003', 'Carol Martinez', 'Computer Science', 3, TRUE FROM users WHERE username = 'student03'
UNION ALL
SELECT user_id, 'STU004', 'David Smith', 'Computer Science', 3, TRUE FROM users WHERE username = 'student04'
UNION ALL
SELECT user_id, 'STU005', 'Eve Johnson', 'Computer Science', 3, TRUE FROM users WHERE username = 'student05'
UNION ALL
SELECT user_id, 'STU006', 'Frank Lee', 'Computer Science', 3, TRUE FROM users WHERE username = 'student06'
UNION ALL
SELECT user_id, 'STU007', 'Grace Park', 'Computer Science', 3, TRUE FROM users WHERE username = 'student07'
UNION ALL
SELECT user_id, 'STU008', 'Henry Patel', 'Computer Science', 3, TRUE FROM users WHERE username = 'student08'
UNION ALL
SELECT user_id, 'STU009', 'Iris Williams', 'Computer Science', 3, TRUE FROM users WHERE username = 'student09'
UNION ALL
SELECT user_id, 'STU010', 'Jack Brown', 'Computer Science', 3, TRUE FROM users WHERE username = 'student10';

-- 7. Enroll students in courses
-- All 10 students -> SE101, Students 1-7 -> DB101, Students 3-10 -> AI101
INSERT INTO course_enrollments (course_id, student_id, enrolled_at)
SELECT c.course_id, s.student_id, NOW()
FROM courses c
JOIN students s ON s.student_number IN ('STU001','STU002','STU003','STU004','STU005','STU006','STU007','STU008','STU009','STU010')
WHERE c.course_code = 'SE101'
UNION ALL
SELECT c.course_id, s.student_id, NOW()
FROM courses c
JOIN students s ON s.student_number IN ('STU001','STU002','STU003','STU004','STU005','STU006','STU007')
WHERE c.course_code = 'DB101'
UNION ALL
SELECT c.course_id, s.student_id, NOW()
FROM courses c
JOIN students s ON s.student_number IN ('STU003','STU004','STU005','STU006','STU007','STU008','STU009','STU010')
WHERE c.course_code = 'AI101';

-- 8. Create class schedule (Mon-Fri, 3x per week schedules)
INSERT INTO class_schedule (course_id, classroom_id, day_of_week, start_time, end_time)
SELECT c.course_id, cls.classroom_id, day, start_t, end_t
FROM (
    SELECT 'SE101'::VARCHAR AS course_code, '101'::VARCHAR AS room_number, 'Monday'::VARCHAR AS day, '09:00:00'::TIME AS start_t, '10:30:00'::TIME AS end_t
    UNION ALL
    SELECT 'SE101', '101', 'Wednesday', '09:00:00', '10:30:00'
    UNION ALL
    SELECT 'SE101', '101', 'Friday', '09:00:00', '10:30:00'
    UNION ALL
    SELECT 'DB101', '102', 'Monday', '11:00:00', '12:30:00'
    UNION ALL
    SELECT 'DB101', '102', 'Wednesday', '11:00:00', '12:30:00'
    UNION ALL
    SELECT 'DB101', '102', 'Friday', '11:00:00', '12:30:00'
    UNION ALL
    SELECT 'AI101', '103', 'Tuesday', '14:00:00', '15:30:00'
    UNION ALL
    SELECT 'AI101', '103', 'Thursday', '14:00:00', '15:30:00'
) sched
JOIN courses c ON c.course_code = sched.course_code
JOIN classrooms cls ON cls.room_number = sched.room_number;

-- 9. Create fingerprint templates for 8 enrolled students (student01-08)
-- Mark 8 students as fp_enrolled
DO $$
DECLARE
    admin_user_id UUID;
    student_ids UUID[];
    sid UUID;
    i INT := 0;
BEGIN
    admin_user_id := (SELECT user_id FROM users WHERE username = 'admin');
    student_ids := ARRAY(
        SELECT s.student_id FROM students s
        WHERE s.student_number IN ('STU001','STU002','STU003','STU004','STU005','STU006','STU007','STU008')
        ORDER BY s.student_number
    );

    FOREACH sid IN ARRAY student_ids LOOP
        i := i + 1;
        UPDATE students
        SET fp_enrolled = TRUE, fp_enrolled_at = NOW(), fp_enrolled_by = admin_user_id
        WHERE student_id = sid;

        INSERT INTO fingerprint_templates (student_id, template_data, template_hash, device_slot, enrolled_by, sync_version, is_active)
        VALUES (
            sid,
            decode(md5('template_' || sid::text || '_' || i::text), 'hex') ||
            decode(md5('template_' || sid::text || '_' || i::text || '_ext'), 'hex'),
            md5('template_' || sid::text),
            i,
            admin_user_id,
            1,
            TRUE
        );
    END LOOP;
END $$;

-- 10. Insert 50 realistic attendance records (weekdays, class hours, last 30 days)
DO $$
DECLARE
    base_date DATE := NOW()::DATE - interval '30 days';
    cur_date DATE;
    cur_day_name TEXT;
    schedule_record RECORD;
    student_ids UUID[];
    random_student_id UUID;
    random_start_time TIME;
    random_offset_minutes INT;
    record_timestamp TIMESTAMPTZ;
    batch_count INT := 0;
BEGIN
    student_ids := ARRAY(
        SELECT s.student_id FROM students s WHERE s.is_active = TRUE ORDER BY s.student_id LIMIT 10
    );

    cur_date := base_date;
    WHILE cur_date <= NOW()::DATE AND batch_count < 50 LOOP
        cur_day_name := TRIM(TO_CHAR(cur_date, 'Day'));

        IF cur_day_name IN ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday') THEN
            SELECT cs.schedule_id, cs.classroom_id, cs.start_time, cl.device_id
            INTO schedule_record
            FROM class_schedule cs
            JOIN classrooms cl ON cl.classroom_id = cs.classroom_id
            WHERE EXTRACT(DOW FROM cur_date) =
                  CASE cur_day_name
                      WHEN 'Monday' THEN 1
                      WHEN 'Tuesday' THEN 2
                      WHEN 'Wednesday' THEN 3
                      WHEN 'Thursday' THEN 4
                      WHEN 'Friday' THEN 5
                  END
            ORDER BY RANDOM()
            LIMIT 1;

            IF schedule_record IS NOT NULL THEN
                FOR j IN 1..6 LOOP
                    IF batch_count >= 50 THEN EXIT; END IF;

                    random_student_id := student_ids[1 + (RANDOM() * 9)::INT];
                    random_offset_minutes := (RANDOM() * 30)::INT;
                    random_start_time := schedule_record.start_time +
                                         (random_offset_minutes || ' minutes')::INTERVAL;
                    record_timestamp := (cur_date::TIMESTAMPTZ + random_start_time::INTERVAL) AT TIME ZONE 'UTC';

                    INSERT INTO attendance_records
                        (student_id, classroom_id, device_id, timestamp, match_score, battery_pct, status, verification_method, created_at)
                    VALUES (
                        random_student_id,
                        schedule_record.classroom_id,
                        schedule_record.device_id,
                        record_timestamp,
                        85 + (RANDOM() * 15)::INT,
                        75 + (RANDOM() * 25)::INT,
                        'present',
                        'fingerprint',
                        NOW()
                    );

                    batch_count := batch_count + 1;
                END LOOP;
            END IF;
        END IF;

        cur_date := cur_date + interval '1 day';
    END LOOP;
END $$;

-- Verify seed data
SELECT COUNT(*) as total_attendance_records FROM attendance_records;
SELECT COUNT(*) as total_enrolled_students FROM students WHERE fp_enrolled = TRUE;
SELECT COUNT(*) as total_users FROM users;

-- MIGRATION v1.1: sync upsert key + future attendance partitions
CREATE UNIQUE INDEX IF NOT EXISTS uq_device_sync_log_device_template ON device_sync_log(device_id, template_id);
CREATE TABLE IF NOT EXISTS attendance_records_2027_01 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-01-01') TO ('2027-02-01');
CREATE TABLE IF NOT EXISTS attendance_records_2027_02 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-02-01') TO ('2027-03-01');
CREATE TABLE IF NOT EXISTS attendance_records_2027_03 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-03-01') TO ('2027-04-01');
CREATE TABLE IF NOT EXISTS attendance_records_2027_04 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-04-01') TO ('2027-05-01');
CREATE TABLE IF NOT EXISTS attendance_records_2027_05 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-05-01') TO ('2027-06-01');
CREATE TABLE IF NOT EXISTS attendance_records_2027_06 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-06-01') TO ('2027-07-01');
CREATE TABLE IF NOT EXISTS attendance_records_2027_07 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-07-01') TO ('2027-08-01');
CREATE TABLE IF NOT EXISTS attendance_records_2027_08 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-08-01') TO ('2027-09-01');
CREATE TABLE IF NOT EXISTS attendance_records_2027_09 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-09-01') TO ('2027-10-01');
CREATE TABLE IF NOT EXISTS attendance_records_2027_10 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-10-01') TO ('2027-11-01');
CREATE TABLE IF NOT EXISTS attendance_records_2027_11 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-11-01') TO ('2027-12-01');
CREATE TABLE IF NOT EXISTS attendance_records_2027_12 PARTITION OF attendance_records
    FOR VALUES FROM ('2027-12-01') TO ('2028-01-01');
