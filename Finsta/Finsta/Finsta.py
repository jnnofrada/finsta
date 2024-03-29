from flask import Flask, render_template, request, session, redirect, url_for, send_file
import os
import uuid
import hashlib
import pymysql.cursors
from functools import wraps
import time

app = Flask(__name__)
app.secret_key = "super secret key"
IMAGES_DIR = os.path.join(os.getcwd(), "images")

connection = pymysql.connect(host="localhost",
                             user="root",
                             password="",
                             db="finsta",
                             charset="utf8mb4",
                             port=3306,
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)


def login_required(f):
    @wraps(f)
    def dec(*args, **kwargs):
        if not "username" in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    
    return dec


@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("home"))
    return render_template("index.html")


@app.route("/home")
@login_required
def home():
    return render_template("home.html", username=session["username"])


@app.route("/upload", methods=["GET"])
@login_required
def upload():
    return render_template("upload.html")


@app.route("/images", methods=["GET"])
@login_required
def images():
    query = "SELECT * FROM photo"
    with connection.cursor() as cursor:
        cursor.execute(query)
    data = cursor.fetchall()
    return render_template("images.html", images=data)


@app.route("/image/<image_name>", methods=["GET"])
def image(image_name):
    image_location = os.path.join(IMAGES_DIR, image_name)
    if os.path.isfile(image_location):
        return send_file(image_location, mimetype="image/jpg")


@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")


@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")


@app.route("/loginAuth", methods=["POST"])
def loginAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()
        
        with connection.cursor() as cursor:
            query = "SELECT * FROM person WHERE username = %s AND password = %s"
            cursor.execute(query, (username, hashedPassword))
        data = cursor.fetchone()
        if data:
            session["username"] = username
            return redirect(url_for("home"))
        
        error = "Incorrect username or password."
        return render_template("login.html", error=error)
    
    error = "An unknown error has occurred. Please try again."
    return render_template("login.html", error=error)


@app.route("/registerAuth", methods=["POST"])
def registerAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()
        firstName = requestData["fname"]
        lastName = requestData["lname"]
        
        try:
            with connection.cursor() as cursor:
                query = "INSERT INTO person (username, password, fname, lname) VALUES (%s, %s, %s, %s)"
                cursor.execute(query, (username, hashedPassword, firstName, lastName))
        except pymysql.err.IntegrityError:
            error = "%s is already taken." % (username)
            return render_template('register.html', error=error)
        
        return redirect(url_for("login"))
    
    error = "An error has occurred. Please try again."
    return render_template("register.html", error=error)


@app.route("/logout", methods=["GET"])
def logout():
    session.pop("username")
    return redirect("/")

#Project 3.3
@app.route("/uploadImage", methods=["POST"])
@login_required
def upload_image():
    imageToUpload = input("Location of the photo: \n")
    allFollowers = input("Visible to All Followers? (Yes/No)")
    if allFollowers == "Yes" or allFollowers == "yes":
        allFollowers = True
    if allFollowers == "No" or allFollowers == "no":
        allFollowers = False
    if request.files:
        image_file = request.files.get(imageToUpload, "")
        image_name = image_file.filename
        filepath = os.path.join(IMAGES_DIR, image_name)
        image_file.save(filepath)
        query = "INSERT INTO photo (timestamp, filePath) VALUES (%s, %s)"
        with connection.cursor() as cursor:
            cursor.execute(query, (time.strftime('%Y-%m-%d %H:%M:%S'), image_name))
        message = "Image has been successfully uploaded."
        query = "UPDATE Photos" \
                "SET allFollowers = %s" \
                "WHERE " \
                "   (   SELECT filepath" \
                "       FROM Photos AS p1" \
                "       WHERE p1.filepath = %s" \
                "   )"
        with connection.cursor as cursor:
            cursor.execute(query, allFollowers, filepath)
        return render_template("upload.html", message=message)
    else:
        message = "Failed to upload image."
        return render_template("upload.html", message=message)


#Project 3
@app.route("/image/<image_name>", methods=["GET"])
@login_required
def find_image(test_user):
    with connection.cursor() as cursor:
        query = "SELECT photoID FROM Photo WHERE (SELECT username FROM Person WHERE IN (SELECT groupName FROM " \
                "SharedWith) AND username = %s"
        cursor.execute(query, test_user)
    data = cursor.fetchall()
    return render_template("images.html", images=data)

#Project 3.1 and 3.2
@app.route("/image", methods=["GET"])
@login_required
def find_images(test_user):
    with connection.cursor() as cursor:
        query = "SELECT photoID, photoPoster, postingdate, filepath " \
                "FROM Photo AS PH1 " \
                "WHERE" \
                "   (   SELECT groupName " \
                "       FROM BelongTo " \
                "       WHERE owner_name = PH1.photoPoster, member_name = %s" \
                "   )" \
                "=" \
                "   (   SELECT groupName " \
                "       FROM SharedWith " \
                "       WHERE groupOwner = PH1.photoPoster" \
                "   )" \
                "ORDER BY postingdate DESC" \
                "SELECT firstname, lastname" \
                "FROM Person AS p1" \
                "WHERE PH1.photoPoster = p1.username" \
                "SELECT username" \
                "FROM Tagged = t1" \
                "WHERE PH1.photoID = t1.photoID AND t1.tagstatus == TRUE" \
                "SELECT username, rating" \
                "FROM Likes AS l1" \
                "WHERE PH1.photoID = l1.photoID"
        cursor.execute(query, test_user)
    data = cursor.fetchall()
    return render_template("images.html", images=data)

#Project 4a
@app.route("/followers", methods=["GET"])
@login_required
def follow():
    followed = input("User to follow: ")
    with connection.cursor() as cursor:
        query = "ALTER TABLE Follow" \
                "ADD acceptedFollow boolean" \
                "UPDATE Follow" \
                "SET acceptedFollow = False" \
                "WHERE" \
                "   (   SELECT username_follower" \
                "       FROM Follow AS f1" \
                "       WHERE" \
                "           (   SELECT username" \
                "               FROM Person AS p1" \
                "               WHERE p1.username = f1.username_follower" \
                "           )" \
                "   )"
        cursor.execute(query)
    data = cursor.fetchall()
    return render_template("followers.html", followers=data)

#Project 4b
@app.route("/followers", methods=["GET"])
@login_required
def manage_follows():
    with connection.cursor() as cursor:
        query = "SELECT username_follower" \
                "FROM Follow as f1" \
                "WHERE f1.acceptedFollow = False"
        if (input("Accept follow? ") == "YES" or "Y"):
            query +=    "UPDATE Follow" \
                        "SET f1.acceptedFollow = True" \
                        "WHERE " + input("Accept follow? ") + " = 'YES'"
        elif (input("Accept follow? ") == "NO" or "N"):
            query +=    "UPDATE Follow" \
                        "SET f1.acceptedFollow = True" \
                        "WHERE " + input("Accept follow? ") + " = 'YES'"
        cursor.execute(query)
    data = cursor.fetchall()
    return render_template("followers.html", followers=data)

#Project 12
@app.route("/groups", methods=["GET"])
@login_required
def add_friendgroup(test_user):
    group_name = input("New Group Name: ")
    with connection.cursor() as cursor:
        find_query =    "SELECT groupName" \
                        "FROM Friendgroup" \
                        "WHERE" \
                        "   (   SELECT username" \
                        "       FROM Person" \
                        "       WHERE username = %s" \
                        "   )"
        cursor.execute(find_query, test_user)
        find_data = cursor.fetchall()
        if (find_data is None):
            message = "Group created"
            query = "INSERT INTO Friendgroup (groupOwner, groupName)" \
                    "VALUES (%s, %s)"
            cursor.execute(query, test_user, group_name)
            return render_template("groups.html", message=message)
        if (find_data is not None):
            message = "Group already exists"
            return render_template("groups.html", message=message)

#Project 13
@app.route("/newFriend", methods=["GET"])
@login_required
def add_friend(test_user):
    new_friend = input("Username of the new friend? ")
    friend_group = input("Add to which group: ")
    with connection.cursor() as cursor:
        find_query =    "SELECT groupName" \
                        "FROM Friendgroup" \
                        "WHERE groupOwner = %s"
        cursor.execute(find_query, test_user)
        find_data = cursor.fetchall()
        find_user = "SELECT member_username" \
                    "FROM BelongTo" \
                    "WHERE member_username = %s"
        cursor.execute(find_user, new_friend)
        user = cursor.fetchall()
        if (find_data is not None) and (user is None):
            message = "Friend added"
            query = "INSERT INTO BelongTo (member_username, owner_username, groupName)" \
                    "VALUES (%s, %s, %s)"
            cursor.execute(query, new_friend, test_user, friend_group)
            return render_template("newFriend.html", message=message)
        elif (find_data is None):
            message = "Group does not exist"
            return render_template("newFriend.html", message=message)
        elif (user is not None):
            message = "Member already in group"
            return render_template("newFriend.html", message=message)

if __name__ == "__main__":
    if not os.path.isdir("images"):
        os.mkdir(IMAGES_DIR)
    app.run()