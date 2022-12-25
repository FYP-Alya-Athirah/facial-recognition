
import mysql.connector
# mysql db
mydb = mysql.connector.connect(
  host="192.168.100.30",
  user="remote",
  password="remote",
  database="schoolmng"
)
mycursor = mydb.cursor()

name="Alya Athirah"
print(type(name))
# Step 1: Find student ID in table "students" based on file names "known_face_names"
sql = "SELECT * FROM students WHERE fullname = %s "
val = [name, ]
mycursor.execute(sql, val)
student_id = mycursor.fetchall()
print(student_id[0][0])
mydb.commit()