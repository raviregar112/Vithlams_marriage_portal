from flask import Flask, render_template, request, redirect, session, flash
from flask import *
from PIL import Image
from functools import wraps
import random
import string
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_connection
import os
import uuid
from werkzeug.utils import secure_filename
from flask import url_for

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads/marriage"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

import os

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "marriage_portal_secret_vithlams"
)

# ==============================
# User Login Required
# ==============================

def login_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect("/login")

        return f(*args, **kwargs)

    return decorated_function


# ==============================
# Admin Login Required
# ==============================

def admin_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if session.get("role") != "admin":
            flash("Please login as Admin.", "danger")
            return redirect("/admin-login")

        return f(*args, **kwargs)

    return decorated_function

### Routess

@app.route("/")
def home():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # ============================
    # Search Filters
    # ============================

    gender = request.args.get("gender", "")
    city = request.args.get("city", "")
    profession = request.args.get("profession", "")
    education = request.args.get("education", "")
    gotra = request.args.get("gotra", "")
    manglik = request.args.get("manglik", "")
    age = request.args.get("age", "")

    query = """
    SELECT *
    FROM marriage_profiles
    WHERE profile_status='Approved'
    """

    values = []

    if gender:
        query += " AND gender=%s"
        values.append(gender)

    if city:
        query += " AND city LIKE %s"
        values.append(f"%{city}%")

    if profession:
        query += " AND profession LIKE %s"
        values.append(f"%{profession}%")

    if education:
        query += " AND education LIKE %s"
        values.append(f"%{education}%")

    if gotra:
        query += " AND self_gotra LIKE %s"
        values.append(f"%{gotra}%")

    if manglik:
        query += " AND manglik=%s"
        values.append(manglik)

    if age:
        query += " AND age=%s"
        values.append(age)

    query += " ORDER BY created_at DESC"

    cursor.execute(query, values)
    marriages = cursor.fetchall()

    # ============================
    # Advertisements
    # ============================

    cursor.execute("""
        SELECT *
        FROM advertisements
        WHERE status='Approved'
        ORDER BY id DESC
    """)
    ads = cursor.fetchall()

    # ============================
    # Homepage Counters
    # ============================

    cursor.execute("""
        SELECT COUNT(*) total
        FROM marriage_profiles
        WHERE profile_status='Approved'
    """)
    total_profiles = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) total
        FROM marriage_profiles
        WHERE gender='Male'
        AND profile_status='Approved'
    """)
    total_grooms = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) total
        FROM marriage_profiles
        WHERE gender='Female'
        AND profile_status='Approved'
    """)
    total_brides = cursor.fetchone()["total"]

    cursor.close()
    conn.close()

    return render_template(
        "index.html",
        marriages=marriages,
        ads=ads,
        total_profiles=total_profiles,
        total_grooms=total_grooms,
        total_brides=total_brides
    )
 #registration pge 

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        full_name = request.form['full_name'].strip()
        mobile = request.form['mobile'].strip()
        email = request.form['email'].strip().lower()
        state = request.form['state']
        city = request.form['city'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Password Match
        if password != confirm_password:
            flash("Password and Confirm Password do not match.", "danger")
            return redirect('/register')

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Check Mobile
        cursor.execute(
            "SELECT id FROM users WHERE mobile=%s",
            (mobile,)
        )

        if cursor.fetchone():

            cursor.close()
            conn.close()

            flash("Mobile Number already registered.", "danger")
            return redirect('/register')

        # Check Email
        cursor.execute(
            "SELECT id FROM users WHERE email=%s",
            (email,)
        )

        if cursor.fetchone():

            cursor.close()
            conn.close()

            flash("Email already registered.", "danger")
            return redirect('/register')

        # Generate Member ID
        cursor.execute("""
            SELECT member_id
            FROM users
            ORDER BY id DESC
            LIMIT 1
        """)

        last_user = cursor.fetchone()

        if last_user and last_user['member_id']:

            last_number = int(last_user['member_id'][3:])
            next_number = last_number + 1

        else:

            next_number = 1

        member_id = f"VTL{next_number:04d}"

        # Password Hash
        hashed_password = generate_password_hash(password)

        # Verification Token
        verification_token = ''.join(
            random.choices(
                string.ascii_letters +
                string.digits,
                k=40
            )
        )

        # Insert User
        cursor.execute("""

        INSERT INTO users
        (
            member_id,
            full_name,
            mobile,
            email,
            state,
            city,
            password,
            email_verified,
            verification_token,
            status
        )

        VALUES
        (
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s
        )

        """,

        (
            member_id,
            full_name,
            mobile,
            email,
            state,
            city,
            hashed_password,
            0,
            verification_token,
            'Pending'
        ))

        conn.commit()

        cursor.close()
        conn.close()

        flash("Registration Successful. Please Login.", "success")

        return redirect('/login')

    return render_template('register.html')


from werkzeug.security import check_password_hash


# Login
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        login_input = request.form['login'].strip()

        password = request.form['password']

        conn = get_connection()

        cursor = conn.cursor(dictionary=True)

        cursor.execute("""

            SELECT *

            FROM users

            WHERE mobile=%s

            OR email=%s

        """,

        (

            login_input,

            login_input

        ))

        user = cursor.fetchone()

        cursor.close()

        conn.close()

        if user:

            if check_password_hash(user['password'], password):

                session['user_id'] = user['id']

                session['member_id'] = user['member_id']

                session['full_name'] = user['full_name']

                session['mobile'] = user['mobile']

                session['email'] = user['email']

                session['profile_photo'] = user['profile_photo'] or 'default.png'

                return redirect('/')

            else:

                flash("Invalid Password","danger")

                return redirect('/login')

        else:

            flash("Mobile Number or Email not found.","danger")

            return redirect('/login')

    return render_template('login.html')

#profile
@app.route('/profile')
@login_required
def profile():

    if 'user_id' not in session:

        return redirect('/login')

    conn = get_connection()

    cursor = conn.cursor(dictionary=True)

    cursor.execute("""

        SELECT *

        FROM users

        WHERE id=%s

    """,

    (

        session['user_id'],

    ))

    user = cursor.fetchone()

    cursor.close()

    conn.close()

    return render_template(

        'profile.html',

        user=user

    )

#Profile Update
@app.route('/upload-profile-photo', methods=['POST'])
@login_required
def upload_profile_photo():

    if 'user_id' not in session:
        return redirect('/login')

    if 'photo' not in request.files:
        return redirect('/profile')

    file = request.files['photo']

    if file.filename == '':
        return redirect('/profile')

    ext = file.filename.rsplit('.',1)[1].lower()

    allowed = ['jpg','jpeg','png','webp']

    if ext not in allowed:

        flash("Only JPG, PNG and WEBP allowed","danger")

        return redirect('/profile')

    filename = str(uuid.uuid4()) + "." + ext

    upload_folder = os.path.join(
        app.root_path,
        'static',
        'uploads',
        'users'
    )

    filepath = os.path.join(upload_folder, filename)

    image = Image.open(file)

    image = image.convert("RGB")

    image.thumbnail((300,300))

    canvas = Image.new("RGB",(300,300),"white")

    x = (300-image.width)//2

    y = (300-image.height)//2

    canvas.paste(image,(x,y))

    canvas.save(filepath,quality=90)

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""

        UPDATE users

        SET profile_photo=%s

        WHERE id=%s

    """,

    (

        filename,

        session['user_id']

    ))

    conn.commit()

    cursor.close()

    conn.close()

    session['profile_photo'] = filename

    flash("Profile photo updated successfully.","success")

    return redirect('/profile')

#profile Edit
@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():

    if 'user_id' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':

        full_name = request.form['full_name']
        email = request.form['email']
        mobile = request.form['mobile']
        state = request.form['state']
        city = request.form['city']

        cursor.execute("""
        UPDATE users
        SET
            full_name=%s,
            email=%s,
            mobile=%s,
            state=%s,
            city=%s
        WHERE id=%s
        """,
        (
            full_name,
            email,
            mobile,
            state,
            city,
            session['user_id']
        ))

        conn.commit()

        session['full_name'] = full_name

        return redirect('/profile')

    cursor.execute("""
    SELECT *
    FROM users
    WHERE id=%s
    """,(session['user_id'],))

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        'edit_profile.html',
        user=user
    )
#id Card
@app.route('/id-card')
@login_required
def id_card():

    if 'user_id' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT *
    FROM users
    WHERE id=%s
    """,(session['user_id'],))

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        'id_card.html',
        user=user
    )

#change Password
@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():

    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':

        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
        SELECT password
        FROM users
        WHERE id=%s
        """, (session['user_id'],))

        user = cursor.fetchone()

        # Old Password Check
        if not check_password_hash(user['password'], current_password):

            cursor.close()
            conn.close()

            return "Current Password is Incorrect"

        # Confirm Password Check
        if new_password != confirm_password:

            cursor.close()
            conn.close()

            return "New Password and Confirm Password do not match"

        # Hash New Password
        hashed_password = generate_password_hash(new_password)

        cursor.execute("""
        UPDATE users
        SET password=%s
        WHERE id=%s
        """, (hashed_password, session['user_id']))

        conn.commit()

        cursor.close()
        conn.close()

        return redirect('/profile')

    return render_template('change_password.html')

#My profile 
@app.route("/my-marriage-profile")
@login_required
def my_marriage_profile():

    if "user_id" not in session:
        return redirect("/login")

    conn=get_connection()

    cursor=conn.cursor(dictionary=True)

    cursor.execute("""

    SELECT *

    FROM marriage_profiles

    WHERE user_id=%s

    LIMIT 1

    """,(session["user_id"],))

    profile=cursor.fetchone()

    cursor.close()

    conn.close()

    return render_template(
        "my_marriage_profile.html",
        profile=profile
    )
#logout
@app.route('/logout')
def logout():

    session.clear()

    return redirect('/login')


#add Marriage
@app.route("/add-marriage", methods=["GET", "POST"])
@login_required
def add_marriage():

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        profile_image = ""

        file = request.files.get("profile_image")

        if file and file.filename != "":

            ext = file.filename.rsplit(".",1)[1].lower()

            filename = str(uuid.uuid4()) + "." + ext

            filepath = os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )

            image = Image.open(file)

            image = image.convert("RGB")

            image.thumbnail((400,400))

            image.save(filepath)

            profile_image = filename


        conn = get_connection()

        cursor = conn.cursor()


        cursor.execute("""

        INSERT INTO marriage_profiles
        (

        user_id,

        member_id,

        profile_status,

        full_name,

        gender,

        date_of_birth,

        age,

        birth_place,

        birth_time,

        height,

        weight,

        manglik,

        religion,

        caste,

        sub_caste,

        self_gotra,

        mother_gotra,

        grandmother_gotra,

        maternal_grandmother_gotra,

        education,

        profession,

        company_name,

        annual_income,

        father_name,

        father_occupation,

        mother_name,

        mother_occupation,

        address,

        state,

        city,

        pincode,

        whatsapp,

        contact_number,

        alternate_contact,

        email,

        profile_image

        )

        VALUES

        (

        %s,%s,%s,

        %s,%s,%s,%s,%s,%s,

        %s,%s,%s,%s,%s,%s,

        %s,%s,%s,%s,

        %s,%s,%s,%s,

        %s,%s,%s,%s,

        %s,%s,%s,%s,

        %s,%s,%s,%s,%s

        )

        """,

        (

        session["user_id"],

        "",

        "Pending",

        request.form["full_name"],

        request.form["gender"],

        request.form["date_of_birth"],

        request.form["age"],

        request.form["birth_place"],

        request.form["birth_time"],

        request.form["height"],

        request.form["weight"],

        request.form["manglik"],

        request.form["religion"],

        request.form["caste"],

        request.form["sub_caste"],

        request.form["self_gotra"],

        request.form["mother_gotra"],

        request.form["grandmother_gotra"],

        request.form["maternal_grandmother_gotra"],

        request.form["education"],

        request.form["profession"],

        request.form["company_name"],

        request.form["annual_income"],

        request.form["father_name"],

        request.form["father_occupation"],

        request.form["mother_name"],

        request.form["mother_occupation"],

        request.form["address"],

        request.form["state"],

        request.form["city"],

        request.form["pincode"],

        request.form["whatsapp"],

        request.form["contact_number"],

        request.form["alternate_contact"],

        request.form["email"],

        profile_image

        )

        )

        profile_id = cursor.lastrowid

        member_id = f"VTL{profile_id:03d}"

        cursor.execute(
            """
            UPDATE marriage_profiles
            SET member_id=%s
            WHERE id=%s
            """,
            (member_id, profile_id)
        )

        conn.commit()

        cursor.close()

        conn.close()

        return redirect("/my-marriage-profile")

    return render_template("marriage/add_marriage.html")

#marriage details
@app.route("/marriage-details/<int:id>")
@login_required
def marriage_details(id):

    if session.get("role") != "admin":
        return redirect("/admin-login")

    conn = get_connection()

    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM marriage_profiles
        WHERE id=%s
    """,(id,))

    profile = cursor.fetchone()

    cursor.close()
    conn.close()

    if not profile:
        return "Profile Not Found"

    return render_template(
        "marriage_details.html",
        profile=profile
    )


@app.route('/add-advertisement', methods=['GET','POST'])
@admin_required
def add_advertisement():

    if request.method == 'POST':

        image = request.files['image']

        filename = ""

        if image and image.filename:

            filename = secure_filename(image.filename)

            image.save(
                os.path.join(
                    'static/uploads/advertisements',
                    filename
                )
            )

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO advertisements
            (
                user_id,
                business_name,
                mobile,
                city,
                image
            )
            VALUES
            (%s,%s,%s,%s,%s)
            """,
            (
                session['user_id'],
                request.form['business_name'],
                request.form['mobile'],
                request.form['city'],
                filename
            )
        )

        conn.commit()

        cursor.close()
        conn.close()

        return redirect('/')

    return render_template(
        'advertisement/add_advertisement.html'
    )
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM admins
            WHERE username=%s
            AND password=%s
        """, (username, password))

        admin = cursor.fetchone()

        cursor.close()
        conn.close()

        if admin:

            session["admin_id"] = admin["id"]
            session["role"] = "admin"

            return redirect("/admin-dashboard")

        else:

            return "Invalid Credentials"

    return render_template("admin/admin_login.html")
#Admin Dashboard
@app.route("/admin-dashboard")
@admin_required
def admin_dashboard():

    if session.get("role") != "admin":
        return redirect("/admin-login")

    conn = get_connection()

    cursor = conn.cursor(dictionary=True)

    # Total Users

    cursor.execute("SELECT COUNT(*) total FROM users")
    users = cursor.fetchone()["total"]

    # Total Marriage Profiles

    cursor.execute("SELECT COUNT(*) total FROM marriage_profiles")
    marriages = cursor.fetchone()["total"]

    # Pending

    cursor.execute("""
    SELECT COUNT(*) total
    FROM marriage_profiles
    WHERE profile_status='Pending'
    """)
    pending = cursor.fetchone()["total"]

    # Approved

    cursor.execute("""
    SELECT COUNT(*) total
    FROM marriage_profiles
    WHERE profile_status='Approved'
    """)
    approved = cursor.fetchone()["total"]

    # Rejected

    cursor.execute("""
    SELECT COUNT(*) total
    FROM marriage_profiles
    WHERE profile_status='Rejected'
    """)
    rejected = cursor.fetchone()["total"]

    # Advertisements

    cursor.execute("SELECT COUNT(*) total FROM advertisements")
    advertisements = cursor.fetchone()["total"]

    # Latest Pending Profiles

    cursor.execute("""
    SELECT *
    FROM marriage_profiles
    WHERE profile_status='Pending'
    ORDER BY created_at DESC
    LIMIT 5
    """)

    latest_pending = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(

        "admin/admin_dashboard.html",

        users=users,

        marriages=marriages,

        pending=pending,

        approved=approved,

        rejected=rejected,

        advertisements=advertisements,


        latest_pending=latest_pending

    )

#manage-marriage
@app.route("/manage-marriages")
@admin_required
def manage_marriages():

    if session.get("role") != "admin":
        return redirect("/admin-login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM marriage_profiles
        ORDER BY created_at DESC
    """)

    marriages = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) total FROM marriage_profiles")
    total = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) total
        FROM marriage_profiles
        WHERE profile_status='Pending'
    """)
    pending = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) total
        FROM marriage_profiles
        WHERE profile_status='Approved'
    """)
    approved = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) total
        FROM marriage_profiles
        WHERE profile_status='Rejected'
    """)
    rejected = cursor.fetchone()["total"]

    cursor.close()
    conn.close()

    return render_template(
        "admin/manage_marriages.html",
        marriages=marriages,
        total=total,
        pending=pending,
        approved=approved,
        rejected=rejected
    )
@app.route('/manage-ads')
@admin_required
def manage_ads():

    if 'admin_id' not in session:
        return redirect('/admin-login')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT *
    FROM advertisements
    ORDER BY id DESC
    """)

    ads = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'admin/manage_ads.html',
        ads=ads
    )
#pending profiles
@app.route("/pending-profiles")
@admin_required
def pending_profiles():

    if session.get("role") != "admin":
        return redirect("/admin-login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM marriage_profiles
        WHERE profile_status='Pending'
        ORDER BY created_at DESC
    """)

    marriages = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin/manage_marriages.html",
        marriages=marriages
    )
@app.route("/approve-profile/<int:id>")
@admin_required
def approve_profile(id):

    if session.get("role") != "admin":
        return redirect("/admin-login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE marriage_profiles
        SET
            profile_status='Approved',
            reject_reason=NULL,
            approved_at=NOW()
        WHERE id=%s
    """, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    # Kis page se aaye the
    page_from = request.args.get("from")

    if page_from == "approved":
        return redirect(url_for("approved_profiles"))

    elif page_from == "rejected":
        return redirect(url_for("rejected_profiles"))

    else:
        return redirect(url_for("pending_profiles"))
    
#reject profiles
@app.route("/reject-profile/<int:id>")
@admin_required
def reject_profile(id):

    if session.get("role") != "admin":
        return redirect("/admin-login")

    reason = request.args.get("reason")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE marriage_profiles
        SET
            profile_status='Rejected',
            reject_reason=%s
        WHERE id=%s
    """, (reason, id))

    conn.commit()

    cursor.close()
    conn.close()

    # Kis page se aaye the
    page_from = request.args.get("from")

    if page_from == "approved":
        return redirect(url_for("approved_profiles"))

    elif page_from == "rejected":
        return redirect(url_for("rejected_profiles"))

    else:
        return redirect(url_for("pending_profiles"))
#delete profiled by admin
@app.route("/delete-marriage/<int:id>")
@admin_required
def delete_marriage(id):

    if session.get("role") != "admin":
        return redirect("/admin-login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM marriage_profiles
        WHERE id=%s
    """, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/pending-profiles")
#approve ads
@app.route('/approve-ad/<int:id>')
@admin_required
def approve_ad(id):

    if 'admin_id' not in session:
        return redirect('/admin-login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE advertisements
    SET status='Approved'
    WHERE id=%s
    """,(id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect('/manage-ads')

#reject ads 
@app.route('/reject-ad/<int:id>')
@admin_required
def reject_ad(id):

    if 'admin_id' not in session:
        return redirect('/admin-login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE advertisements
    SET status='Rejected'
    WHERE id=%s
    """,(id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect('/manage-ads')
#delete Ads
@app.route('/delete-ad/<int:id>')
@admin_required
def delete_ad(id):

    if 'admin_id' not in session:
        return redirect('/admin-login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM advertisements
    WHERE id=%s
    """,(id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect('/manage-ads')


if __name__ == '__main__':
    app.run(debug=True)