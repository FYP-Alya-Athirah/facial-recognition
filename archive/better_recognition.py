import face_recognition
import cv2
import numpy as np
import mysql.connector
import os
from datetime import datetime
from flask import Flask, render_template, Response

# This is a demo of running face recognition on live video from your webcam. It's a little more complicated than the
# other example, but it includes some basic performance tweaks to make things run a lot faster:
#   1. Process each video frame at 1/4 resolution (though still display it at full resolution)
#   2. Only detect faces in every other frame of video.

# Get a reference to webcam #0 (the default one)
video_capture = cv2.VideoCapture(0)
# video_capture = cv2.VideoCapture('http://192.168.100.35:8000/stream.mjpg')

#Initialize arrays for dataset
users_image_paths=[]
users_images=[]
users_encodings=[]
users_labels=[]

# laravel public directory
directory = "D:/Github/web2/public/images/"
# directory = "faces/"

# Seed by individual file name
# users_image_paths = os.listdir(directory) #not included /faces/
# users_labels = [x.split('.')[0] for x in users_image_paths] # get names based on file names in array
# for x in range(len(users_image_paths)):
#     users_image_paths[x]=directory+users_image_paths[x]
# for x in users_image_paths:
#     users_images.append(face_recognition.load_image_file(x))
# for x in users_images:
#     users_encodings.append(face_recognition.face_encodings(x)[0])

# Seed by parent directory name
users_name_directory = os.listdir(directory)
# users_labels = [x.split('.')[0] for x in users_image_paths] # every directory found
for x in range(len(users_name_directory)):
    users_image_paths = os.listdir(directory+users_name_directory[x])
    for y in range(len(users_image_paths)):
        # load image then encode
        image = face_recognition.load_image_file(directory+users_name_directory[x]+"/"+users_image_paths[y])
        users_encodings.append(face_recognition.face_encodings(image)[0])
        # append to label array
        users_labels.append(users_name_directory[x])


# Create arrays of known face encodings and their names
# HOT: create array based on folder to encodings
known_face_encodings = users_encodings
# HOT: create array based on file names
known_face_names = users_labels


# Initialize some variables
face_locations = []
face_encodings = []
face_names = []
process_this_frame = True

# mysql db
mydb = mysql.connector.connect(
  host="192.168.100.30",
  user="remote",
  password="remote",
  database="schoolmng",
)
mycursor = mydb.cursor()


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
                print("found best match\n")
                name = known_face_names[best_match_index]
                now = datetime.now()
                formatted_date = now.strftime('%Y-%m-%d')
                formatted_time = now.strftime('%H:%M:%S')
                #DANGER
                # Step 1: Check if day is morning(attendance 5:00am - 8:00am) or evening(dismissal 11:00am -8:00pm)
                # Step 2: Check if name is a student/parent/teacher
                # If student -> directly set attendance/dismissal
                # If parent -> get all students with that parent and set attendance/dismissal
                # If teacher -> directly set attendance/dismissal

                #Step 1: Find student ID in table "students" based on file names "known_face_names"
                sql = "SELECT * FROM students WHERE fullname = %s"
                val = [name]
                mycursor.execute(sql, val)
                student_id = mycursor.fetchall()
                mydb.commit()
                student_id = student_id[0][0]

                #Step 2: Check in record_attendance if student is logged today(optional)
                sql = "SELECT * FROM record_attendance WHERE person_id = %s AND role = 1 AND date = %s"
                val = [student_id, formatted_date]
                mycursor.execute(sql, val)
                mycursor.fetchall()
                mydb.commit()

                if(mycursor.rowcount==0):
                    # Step 3: Insert into DB table "record_attendance" with role,student_id,temp_id,date,time
                    sql = "INSERT INTO record_attendance (person_id, role, date, time) VALUES (%s,%s,%s,%s)"
                    val = [student_id, 1, formatted_date, formatted_time]
                    mycursor.execute(sql, val)
                    mydb.commit()
                    #  Update in students table too
                    sql = "UPDATE students SET attend = 1 WHERE fullname = %s"
                    val = [name]
                    mycursor.execute(sql, val)
                    mydb.commit()



                #DONE
            face_names.append(name)

    process_this_frame = not process_this_frame


    # Display the results
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        # Scale back up face locations since the frame we detected in was scaled to 1/4 size
        top *= 4
        right *= 4
        bottom *= 4
        left *= 4

        # Draw a box around the face
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

        # Draw a label with a name below the face
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

    # Display the resulting image
    cv2.imshow('Video', frame)



    # Hit 'q' on the keyboard to quit!
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break


# Release handle to the webcam
video_capture.release()
cv2.destroyAllWindows()
