import face_recognition
import cv2
import numpy as np
import mysql.connector
import os
import datetime
from flask import Flask, render_template, Response
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading


# This is a demo of running face recognition on live video from your webcam. It's a little more complicated than the
# other example, but it includes some basic performance tweaks to make things run a lot faster:
#   1. Process each video frame at 1/4 resolution (though still display it at full resolution)
#   2. Only detect faces in every other frame of video.

app = Flask(__name__)
# Get a reference to webcam #0 (the default one)
video_capture = cv2.VideoCapture(0)
# video_capture = cv2.VideoCapture('http://192.168.100.35:8000/stream.mjpg')


# laravel public directory
directory = "D:/Github/web2/public/images/"
# directory = "/home/pie/faces/"

# Seed by parent directory name
users_name_directory = os.listdir(directory)

process_this_frame = True

# mysql db
mydb = mysql.connector.connect(
  host="192.168.100.30",
  user="remote",
  password="remote",
  database="schoolmng",
)
mycursor = mydb.cursor()
directory_update = False


class PeriodicThread(threading.Thread):

    def __init__(self, interval):
        self.stop_event = threading.Event()
        self.interval = interval
        super(PeriodicThread, self).__init__()

    def run(self):
         while not self.stop_event.is_set():
             self.main()
             # wait self.interval seconds or until the stop_event is set
             self.stop_event.wait(self.interval)

    def terminate(self):
        self.stop_event.set()

    def main(self):
       gen_frames()

def gen_frames():  # generate frame by frame from camera
    global process_this_frame
    print("global")
    print("Dataset Loading")
    # Initialize arrays for dataset
    users_encodings = []
    users_labels = []
    # users_labels = [x.split('.')[0] for x in users_image_paths] # every directory found
    for x in range(len(users_name_directory)):
        users_image_paths = os.listdir(directory + users_name_directory[x])
        for y in range(len(users_image_paths)):
            # load image then encode
            image = face_recognition.load_image_file(directory + users_name_directory[x] + "/" + users_image_paths[y])
            users_encodings.append(face_recognition.face_encodings(image)[0])
            # append to label array
            users_labels.append(users_name_directory[x])

    # Create arrays of known face encodings and their names
    known_face_encodings = users_encodings
    known_face_names = users_labels

    print("Dataset Loaded")
    # Initialize some variables
    face_locations = []
    face_encodings = []
    face_names = []

    while True:
        # Grab a single frame of video
        ret, frame = video_capture.read()

        # Only process every other frame of video to save time
        if process_this_frame:
            # Resize frame of video to 1/4 size for faster face recognition processing
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

            # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
            rgb_small_frame = small_frame[:, :, ::-1]

            # Find all the faces and face encodings in the current frame of video
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            face_names = []
            for face_encoding in face_encodings:
                # See if the face is a match for the known face(s)
                matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                name = "Unknown"

                # # If a match was found in known_face_encodings, just use the first one.
                # if True in matches:
                #     first_match_index = matches.index(True)
                #     name = known_face_names[first_match_index]

                # Or instead, use the known face with the smallest distance to the new face
                face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = known_face_names[best_match_index]
                    print("Face detected: "+name)
                    now = datetime.datetime.now()
                    formatted_date = now.strftime('%Y-%m-%d')
                    formatted_time = now.strftime('%H:%M:%S')

                    temptime = datetime.time(12,0,0)
                    # Step 1: Get the id and role
                    role, id = check_role(name)

                    # Step 2: Check if day is morning(attendance 5:00am - 8:00am) or evening(dismissal 11:00am -8:00pm)
                    if time_in_range(datetime.time(5,0,0), datetime.time(8,0,0), temptime):
                        if(role == 1 and person_attended_today(id, role, formatted_date)):
                            set_attendance_student(name, id, formatted_date, formatted_time)
                        if (role == 3 and person_attended_today(id, role, formatted_date)):
                            set_attendance_teacher(name, id, formatted_date, formatted_time)

                    elif time_in_range(datetime.time(11, 0, 0), datetime.time(20, 0, 0), temptime):
                        if(role == 2):
                            students = get_children(id)
                            for i in range(len(students)):
                                if(not person_attended_today(students[i][0], 1, formatted_date) and person_dismissed_today(students[i][0], 1, formatted_date)):
                                    set_dismissal_student_parent(students[i][1], students[i][0], formatted_date, formatted_time, name)
                        elif(role == 1):
                            if (person_dismissed_today(id, 1, formatted_date)):
                                set_dismissal_student(name, id, formatted_date, formatted_time)
                        elif (role == 3):
                            if (person_dismissed_today(id, 3, formatted_date)):
                                set_dismissal_teacher(name, id, formatted_date, formatted_time)

                face_names.append(name)


        process_this_frame = not process_this_frame

        if (directory_update):
            break



def time_in_range(start, end, x):
    """Return true if x is in the range [start, end]"""
    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end
def check_role(name):
    # Check if its a student
    sql = "SELECT * FROM students WHERE fullname = %s"
    val = [name]
    mycursor.execute(sql, val)
    student = mycursor.fetchall()
    mydb.commit()
    if (mycursor.rowcount != 0):
        return 1, student[0][0]

    # Check if its a teacher
    sql = "SELECT * FROM teachers WHERE fullname = %s"
    val = [name]
    mycursor.execute(sql, val)
    teacher = mycursor.fetchall()
    mydb.commit()
    if (mycursor.rowcount != 0):
        return 3, teacher[0][0]

    # Check if its a student
    sql = "SELECT * FROM parents WHERE fullname = %s"
    val = [name]
    mycursor.execute(sql, val)
    parent = mycursor.fetchall()
    mydb.commit()
    if (mycursor.rowcount != 0):
        return 2, parent[0][0]

    return 0, 0

def set_attendance_student(name, student_id, formatted_date, formatted_time):
    # Insert into DB table "record_attendance" with role,student_id,temp_id,date,time
    sql = "INSERT INTO record_attendance (person_id, role, date, time) VALUES (%s,%s,%s,%s)"
    val = [student_id, 1, formatted_date, formatted_time]
    mycursor.execute(sql, val)
    mydb.commit()
    #  Update in students table too
    sql = "UPDATE students SET attend = 1, time=%s, parent=%s WHERE fullname = %s"
    val = [formatted_time, "none", name]
    mycursor.execute(sql, val)
    mydb.commit()
    print("Attendance updated in database for: ", name)

def set_attendance_teacher(name, teacher_id, formatted_date, formatted_time):
    # Insert into DB table "record_attendance"
    sql = "INSERT INTO record_attendance (person_id, role, date, time) VALUES (%s,%s,%s,%s)"
    val = [teacher_id, 3, formatted_date, formatted_time]
    mycursor.execute(sql, val)
    mydb.commit()
    #  Update in teachers table too
    sql = "UPDATE teachers SET attend = 1, time=%s WHERE fullname = %s"
    val = [formatted_time,  name]
    mycursor.execute(sql, val)
    mydb.commit()
    print("Attendance updated in database for: ", name)

def person_attended_today(id, role, formatted_date):
    # Check in record_attendance if student is logged today(optional)
    sql = "SELECT * FROM record_attendance WHERE person_id = %s AND role = %s AND date = %s"
    val = [id, role, formatted_date]
    mycursor.execute(sql, val)
    mycursor.fetchall()
    mydb.commit()

    if (mycursor.rowcount == 0):
        return True
    else:
        return False

def person_dismissed_today(id, role, formatted_date):
    # Check in record_attendance if student is logged today(optional)
    sql = "SELECT * FROM record_dismissal WHERE person_id = %s AND role = %s AND date = %s"
    val = [id, role, formatted_date]
    mycursor.execute(sql, val)
    mycursor.fetchall()
    mydb.commit()

    if (mycursor.rowcount == 0):
        return True
    else:
        return False

def set_dismissal_student_parent(name, student_id, formatted_date, formatted_time, parent):
    # Insert into DB table "record_attendance" with role,student_id,temp_id,date,time
    sql = "INSERT INTO record_dismissal (person_id, role, date, time) VALUES (%s,%s,%s,%s)"
    val = [student_id, 1, formatted_date, formatted_time]
    mycursor.execute(sql, val)
    mydb.commit()
    #  Update in students table too
    sql = "UPDATE students SET attend = 2, time=%s, parent=%s WHERE fullname = %s"
    val = [formatted_time, parent, name]
    mycursor.execute(sql, val)
    mydb.commit()
    print("Dismissal updated in database for: ", name)

def set_dismissal_student(name, student_id, formatted_date, formatted_time):
    # Insert into DB table "record_attendance" with role,student_id,temp_id,date,time
    sql = "INSERT INTO record_dismissal (person_id, role, date, time) VALUES (%s,%s,%s,%s)"
    val = [student_id, 1, formatted_date, formatted_time]
    mycursor.execute(sql, val)
    mydb.commit()
    #  Update in students table too
    sql = "UPDATE students SET attend = 2, time=%s, parent=%s WHERE fullname = %s"
    val = [formatted_time, "none", name]
    mycursor.execute(sql, val)
    mydb.commit()
    print("Dismissal updated in database for: ", name)

def set_dismissal_teacher(name, id, formatted_date, formatted_time):
    # Insert into DB table "record_attendance" with role,student_id,temp_id,date,time
    sql = "INSERT INTO record_dismissal (person_id, role, date, time) VALUES (%s,%s,%s,%s)"
    val = [id, 3, formatted_date, formatted_time]
    mycursor.execute(sql, val)
    mydb.commit()
    #  Update in students table too
    sql = "UPDATE teachers SET attend = 2, time=%s WHERE fullname = %s"
    val = [formatted_time, name]
    mycursor.execute(sql, val)
    mydb.commit()
    print("Dismissal updated in database for: ", name)
def get_children(id):
    # get students under parent
    sql = "SELECT * FROM students INNER JOIN parent_student ON parent_student.student_id = students.id WHERE parent_student.parent_id = %s"
    val = [id]
    mycursor.execute(sql, val)
    students = mycursor.fetchall()
    mydb.commit()
    return students

@app.route('/video_feed')
def video_feed():
    #Video streaming route. Put this in the src attribute of an img tag
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')

def flask_app():
    app.run(host='0.0.0.0', port=5000)

class Watcher:
    DIRECTORY_TO_WATCH = directory
    def __init__(self):
        self.observer = Observer()

    def run(self):
        print("Watcher Started")
        event_handler = Handler()
        self.observer.schedule(event_handler, self.DIRECTORY_TO_WATCH, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(5)
        except:
            self.observer.stop()
            print ("Error")

        self.observer.join()


class Handler(FileSystemEventHandler):
    @staticmethod
    def on_any_event(event):
        update = False
        if event.is_directory:
            return None

        elif event.event_type == 'created':
            # Take any action here when a file is first created.
            print ("Received created event - %s." % event.src_path)
            update = True

        elif event.event_type == 'modified':
            # Taken any action here when a file is modified.
            print ("Received modified event - %s." % event.src_path)
            update = True

        elif event.event_type == 'deleted':
            # Taken any action here when a file is modified.
            print ("Received deleted event - %s." % event.src_path)
            update = True

        global directory_update
        directory_update = update

def run_watcher():
    w = Watcher()
    w.run()
# if __name__ == '__main__':


t1 = threading.Thread(target=gen_frames, name='t1')
t2 = threading.Thread(target=run_watcher, name='t2')
t1.start()
t2.start()
# while True:
#     time.sleep(3)
#     print(directory_update)
#     if (directory_update):
#         t1.join()
#         print("Thread 1 joined")
#         t1 = threading.Thread(target=gen_frames, name='t1')
#         t1.start()
#         directory_update = False
# worker = PeriodicThread(interval=5)
# worker.start()
while True:
    time.sleep(3)
    print(directory_update)
    if (directory_update):
        directory_update = False
        print("Thread 1 joining")
        t1.join()
        print("Thread 1 joined")
        time.sleep(5)
        t1 = threading.Thread(target=gen_frames, name='t1')
        t1.start()
# worker.join()
t2.join()

# Release handle to the webcam
video_capture.release()
cv2.destroyAllWindows()



