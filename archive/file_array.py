
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
sql = "SELECT * FROM students INNER JOIN parent_student ON parent_student.student_id = students.id WHERE parent_student.parent_id = %s"
val = [15]
mycursor.execute(sql, val)
# student_id = mycursor.fetchall()

mydb.commit()
print(mycursor.fetchall())