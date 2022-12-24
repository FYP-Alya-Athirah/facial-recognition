import os
users_image_paths = os.listdir("faces") #not included /faces/
users_labels = [x.split('.')[0] for x in os.listdir("faces")]
print(users_image_paths)
print(users_labels)