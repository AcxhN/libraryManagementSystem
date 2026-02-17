from flask import Flask, request, render_template_string, redirect, url_for, flash
import sqlite3
from datetime import datetime,timedelta
import os

app = Flask(__name__)
app.secret_key = 'secretkey'


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'library.db')


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# Home page with links to all operations
@app.route('/')
def index():
    return render_template_string('''
        <h1>Library Database Application</h1>
        <ul>
            <li><a href="{{ url_for('find_item') }}">Find an Item</a></li>
            <li><a href="{{ url_for('borrow_item') }}">Borrow an Item</a></li>
            <li><a href="{{ url_for('return_item') }}">Return a Borrowed Item</a></li>
            <li><a href="{{ url_for('donate_item') }}">Donate an Item</a></li>
            <li><a href="{{ url_for('find_event') }}">Find an Event</a></li>
            <li><a href="{{ url_for('register_event') }}">Register for an Event</a></li>
            <li><a href="{{ url_for('volunteer') }}">Volunteer for the Library</a></li>
            <li><a href="{{ url_for('ask_help') }}">Ask for Help from a Librarian</a></li>
        </ul>
    ''')


@app.route('/find_item', methods=['GET', 'POST'])
def find_item():
    results = []
    conn = get_db_connection()
    if request.method == 'POST':
        search = request.form['search']
        query = """
            SELECT li.id, li.title, li.itemType, li.status,
                   group_concat(a.firstName || ' ' || a.lastName, ', ') as authors
            FROM libraryItem li
            LEFT JOIN item_author ia ON li.id = ia.itemid
            LEFT JOIN author a ON ia.authorid = a.id
            WHERE li.title LIKE ? 
            GROUP BY li.id
        """
        params = ('%' + search + '%',)
    else:
        query = """
            SELECT li.id, li.title, li.itemType, li.status,
                   group_concat(a.firstName || ' ' || a.lastName, ', ') as authors
            FROM libraryItem li
            LEFT JOIN item_author ia ON li.id = ia.itemid
            LEFT JOIN author a ON ia.authorid = a.id
            GROUP BY li.id
        """
        params = ()
    cur = conn.execute(query, params)
    results = cur.fetchall()
    conn.close()
    return render_template_string('''
        <h2>Find an Item</h2>
        <form method="post">
            <input type="text" name="search" placeholder="Enter item title">
            <input type="submit" value="Search">
        </form>
        {% if results %}
            <h3>Results:</h3>
            <ul>
                {% for item in results %}
                    <li>
                      {{ item['id'] }} - {{ item['title'] }} ({{ item['itemType'] }}) - Status: {{ item['status'] }}
                      {% if item['authors'] %}
                          - Authors: {{ item['authors'] }}
                      {% else %}
                          - No authors listed.
                      {% endif %}
                    </li>
                {% endfor %}
            </ul>
        {% else %}
            <p>No items found.</p>
        {% endif %}
        <a href="{{ url_for('index') }}">Back to Home</a>
    ''', results=results)



@app.route('/borrow_item', methods=['GET', 'POST'])
def borrow_item():
    if request.method == 'POST':
        try:
            member_id = request.form['member_id'].strip()
            item_id = request.form['item_id'].strip()

            if not member_id or not item_id:
                flash("Both Member ID and Item ID are required.")
                return redirect(url_for('borrow_item'))

            conn = get_db_connection()

            cur = conn.execute("SELECT id FROM member WHERE id = ?", (member_id,))
            if not cur.fetchone():
                flash("The provided Member ID does not exist.")
                conn.close()
                return redirect(url_for('borrow_item'))

            cur = conn.execute("SELECT id, status FROM libraryItem WHERE id = ?", (item_id,))
            item = cur.fetchone()
            if not item:
                flash("The provided Item ID does not exist.")
                conn.close()
                return redirect(url_for('borrow_item'))
            if item['status'] != 'available':
                flash("This item is not available for borrowing.")
                conn.close()
                return redirect(url_for('borrow_item'))

            # Calculate due date as 14 days from now.
            due_date = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')

            conn.execute("INSERT INTO loan (itemid, memberid) VALUES (?, ?)",
                         (item_id, member_id))
            loan_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.commit()
            conn.close()

            flash(f"Item borrowed successfully! It is due on {due_date}. Your LoanID is {loan_id}"
                                                f", please note it down for future return")
        except Exception as e:
            flash("Error borrowing item: " + str(e))
        return redirect(url_for('borrow_item'))

    return render_template_string('''
        <h2>Borrow an Item</h2>
        <form method="post">
            Member ID: <input type="text" name="member_id"><br>
            Item ID: <input type="text" name="item_id"><br>
            <p>Due date is automatically set to 14 days from today.</p>
            <input type="submit" value="Borrow">
        </form>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <ul>
              {% for message in messages %}
                <li>{{ message }}</li>
              {% endfor %}
            </ul>
          {% endif %}
        {% endwith %}
        <a href="{{ url_for('index') }}">Back to Home</a>
    ''')


@app.route('/return_item', methods=['GET', 'POST'])
def return_item():
    if request.method == 'POST':
        try:
            loan_id = request.form['loan_id']
            returned_date = request.form.get('returned_date') or datetime.now().strftime('%Y-%m-%d')
            if not returned_date:
                flash("Please enter in valid format")
                return redirect(url_for('loan'))
            conn = get_db_connection()
            conn.execute("UPDATE loan SET returnedDate = ? WHERE id = ?", (returned_date, loan_id))
            conn.commit()
            conn.close()
            flash("Item returned successfully!")
        except Exception as e:
            flash("Error returning item: " + str(e))
        return redirect(url_for('return_item'))
    return render_template_string('''
        <h2>Return a Borrowed Item</h2>
        <form method="post">
            Loan ID: <input type="text" placeholder="Loan ID were given to you" name="loan_id"><br>
            Returned Date (YYYY-MM-DD): <input type="text" placeholder="default is today" name="returned_date"><br>
            <input type="submit" value="Return">
        </form>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <ul>
              {% for message in messages %}
                <li>{{ message }}</li>
              {% endfor %}
            </ul>
          {% endif %}
        {% endwith %}
        <a href="{{ url_for('index') }}">Back to Home</a>
    ''')


@app.route('/donate_item', methods=['GET', 'POST'])
def donate_item():
    if request.method == 'POST':
        try:
            title = request.form['title']
            publication_date = request.form['publication_date']
            item_type = request.form['item_type']
            author_first = request.form['author_first']
            author_last = request.form['author_last']

            try:
                datetime.strptime(publication_date, '%Y-%m-%d')
            except ValueError:
                flash("Invalid publication date. Please use YYYY-MM-DD format.")
                return redirect(url_for('donate_item'))

            if not author_first.strip() or not author_last.strip():
                flash("Author's first and last name are required.")
                return redirect(url_for('donate_item'))

            conn = get_db_connection()
            cur = conn.execute("INSERT INTO libraryItem (title, publicationDate, itemType) VALUES (?, ?, ?)",
                               (title, publication_date, item_type))

            item_id = cur.lastrowid

            cur = conn.execute("SELECT id from author WHERE firstname = ? AND lastname = ?",
                               (author_first, author_last))
            author = cur.fetchone()
            if author:
                author_id = author['id']
            else:
                cur = conn.execute("INSERT INTO author (firstName, lastName) VALUES (?, ?)",
                                   (author_first, author_last))
                author_id = cur.lastrowid

            conn.execute("INSERT INTO item_author(itemid, authorid) VALUES (?,?)", (item_id, author_id))

            conn.commit()
            conn.close()
            flash("Item donated successfully!")
        except Exception as e:
            flash("Error donating item: " + str(e))
        return redirect(url_for('donate_item'))
    return render_template_string('''
        <h2>Donate an Item</h2>
        <form method="post">
            Title: <input type="text" placeholder="Item name" name="title"><br>
            Publication Date (YYYY-MM-DD): <input type="text" placeholder="Publication date" name="publication_date"><br>
            Item Type: <input type="text" placeholder="print book, cd, record, etc" name="item_type"><br>
            Author's name: <input type="text" placeholder="First name" name="author_first">
            <input type="text" placeholder="Last name" name="author_last"><br>
            <input type="submit" value="Donate">
        </form>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <ul>
              {% for message in messages %}
                <li>{{ message }}</li>
              {% endfor %}
            </ul>
          {% endif %}
        {% endwith %}
        <a href="{{ url_for('index') }}">Back to Home</a>
    ''')


@app.route('/find_event', methods=['GET', 'POST'])
def find_event():
    conn = get_db_connection()
    if request.method == 'POST':
        search = request.form['search']
        query = """
            SELECT e.id, e.name, e.eventDate, et.name as eventType, e.targetAudience, e.roomid
            FROM event e 
            JOIN eventType et ON e.eventTypeid = et.id
            WHERE e.name LIKE ?
        """
        params=('%' + search + '%',)
    else:
        # GET: no filter, show all events.
        query = """
            SELECT e.id, e.name, e.eventDate, et.name as eventType, e.targetAudience, r.name as roomName, e.roomid
            FROM event e 
            JOIN eventType et ON e.eventTypeid = et.id
            JOIN room r ON r.id = e.roomid
        """
        params = ()
    cur = conn.execute(query, params)
    events = cur.fetchall()
    conn.close()
    return render_template_string('''
        <h2>Find an Event</h2>
        <form method="post">
            <input type="text" name="search" placeholder="Enter event name">
            <input type="submit" value="Search">
        </form>
        {% if events %}
            <h3>Events:</h3>
            <ul>
                {% for event in events %}
                    <li>
                        {{event['roomid']}} - "{{ event['name'] }} on {{ event['eventDate'] }}", Room: {{ event['roomName'] }}
                        (Event type: {{ event['eventType'] }}, Recommended for {{ event['targetAudience'] }})
                    </li>
                {% endfor %}
            </ul>
        {% else %}
            <p>No event found.</p>
        {% endif %}
        <a href="{{ url_for('index') }}">Back to Home</a>
    ''', events=events)


@app.route('/register_event', methods=['GET', 'POST'])
def register_event():
    if request.method == 'POST':
        event_id = request.form['event_id'].strip()
        member_id = request.form['member_id'].strip()

        # Validate that both fields are provided
        if not event_id or not member_id:
            flash("Both Event ID and Member ID are required.")
            return redirect(url_for('register_event'))

        conn = get_db_connection()
        try:
            # Check if the event exists
            cur = conn.execute("SELECT id FROM event WHERE id = ?", (event_id,))
            if not cur.fetchone():
                flash("The provided Event ID does not exist.")
                conn.close()
                return redirect(url_for('register_event'))

            # Check if the member exists
            cur = conn.execute("SELECT id FROM member WHERE id = ?", (member_id,))
            if not cur.fetchone():
                flash("The provided Member ID does not exist.")
                conn.close()
                return redirect(url_for('register_event'))

            # If both exist, insert the registration
            conn.execute("INSERT INTO eventRegistration (eventid, memberid) VALUES (?, ?)",
                         (event_id, member_id))
            conn.commit()
            flash("Registered for event successfully!")
        except Exception as e:
            flash("Error registering for event: " + str(e))
        finally:
            conn.close()
        return redirect(url_for('register_event'))
    return render_template_string('''
        <h2>Register for an Event</h2>
        <form method="post">
            Event ID: <input type="text" name="event_id"><br>
            Member ID: <input type="text" name="member_id"><br>
            <input type="submit" value="Register">
        </form>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <ul>
              {% for message in messages %}
                <li>{{ message }}</li>
              {% endfor %}
            </ul>
          {% endif %}
        {% endwith %}
        <a href="{{ url_for('index') }}">Back to Home</a>
    ''')


@app.route('/volunteer', methods=['GET', 'POST'])
def volunteer():
    if request.method == 'POST':
        try:
            # Gather new member information
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            email = request.form['email']
            phone = request.form['phone']

            if not first_name.strip() or not last_name.strip():
                flash("First and last name are required.")
                return redirect(url_for('donate_item'))
            if not email.strip() or not phone.strip():
                flash("Your contact information are required.")
                return redirect(url_for('donate_item'))

            conn = get_db_connection()
            # Check if the member already exists (using email as a unique identifier)
            cur = conn.execute("SELECT id FROM member WHERE email = ?", (email,))
            member = cur.fetchone()
            if member:
                member_id = member['id']
            else:
                # Create a new member record if not found
                cur = conn.execute(
                    "INSERT INTO member (firstName, lastName, email, joinDate) VALUES (?, ?, ?, date('now'))",
                    (first_name, last_name, email)
                )
                member_id = cur.lastrowid
                flash(f"You are not a member of the library, we have registered you as a member, your member id is: {member_id}. Thank you for volunteering")

            cur = conn.execute("SELECT id from personnel where memberid = ? AND jobTitle = 'volunteer' ", (member_id,))
            if cur.fetchone():
                flash("You have already volunteered")
                conn.close()
                return redirect(url_for('volunteer'))

            conn.execute(
                "INSERT INTO personnel (memberid, jobTitle, phone) VALUES (?, 'volunteer', ?)",
                (member_id, phone)
            )
            conn.commit()
            conn.close()
            flash("Volunteer registration successful!")
        except Exception as e:
            flash("Error registering volunteer: " + str(e))
        return redirect(url_for('volunteer'))
    return render_template_string('''
        <h2>Volunteer for the Library</h2>
        <form method="post">
            First Name: <input type="text" name="first_name" placeholder="Your first name"><br>
            Last Name: <input type="text" name="last_name" placeholder="Your last name"><br>
            Email: <input type="text" name="email" placeholder="Your email"><br>
            Phone: <input type="text" name="phone" placeholder="Your phone number"><br>
            <input type="submit" value="Volunteer">
        </form>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <ul>
              {% for message in messages %}
                <li>{{ message }}</li>
              {% endfor %}
            </ul>
          {% endif %}
        {% endwith %}
        <a href="{{ url_for('index') }}">Back to Home</a>
    ''')


@app.route('/ask_help', methods=['GET', 'POST'])
def ask_help():
    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        message = request.form['message']
        flash("Your help request has been submitted. A librarian will contact you soon!")
        return redirect(url_for('ask_help'))
    return render_template_string('''
        <h2>Ask for Help from a Librarian</h2>
        <form method="post">
            Name: <input type="text" placeholder="Tell us your name" name="name"><br>
            Where: <input type="text" placeholder="Tell us where you are" name="location"><br>
            Your Message: <br> <textarea placeholder="What do you need help with?" name="message"></textarea><br>
            <input type="submit" value="Submit Request">
        </form>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <ul>
              {% for message in messages %}
                <li>{{ message }}</li>
              {% endfor %}
            </ul>
          {% endif %}
        {% endwith %}
        <a href="{{ url_for('index') }}">Back to Home</a>
    ''')


if __name__ == '__main__':
    app.run(debug=True)
