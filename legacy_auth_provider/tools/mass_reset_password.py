import argparse
import mysql.connector
import random
import string
from arxiv.auth.legacy.passwords import hash_password

# Function to generate a random password
def generate_random_password(length=10):
    characters = string.ascii_letters + string.digits + "-_*()^%$#!{}[]+;:/"
    return ''.join(random.choice(characters) for _i in range(length))


def hack_creds(database_url, start_id, count):
    # Parse the URL (assuming it's in a standard format)
    # You can use urllib.parse.urlparse for more complex parsing if needed
    url_parts = database_url.split('/')
    db_name = url_parts[-1]
    host_and_port = url_parts[0].split('@')[-1]
    host, port = host_and_port.split(':')
    user, password = url_parts[0].split('@')[0].split(':')

    # Establish the connection to the database
    connection = mysql.connector.connect(
        host=host,
        port=int(port),
        user=user,
        password=password,
        database=db_name
    )

    # Create a cursor object to interact with the database
    cursor = connection.cursor()

    # Fetch the specified number of rows from the "users" table
    cursor.execute(f"SELECT user_id, email FROM tapir_users where user_id >= {start_id} LIMIT {count+100}")
    user_ids = [ (cols[0], cols[1]) for cols in cursor.fetchall()]

    sofar = 0
    with open("creds.csv", "a+", encoding="utf-8") as creds_file:
        # Update the password for each fetched user_id
        email: str
        for user_id, email in user_ids:
            if "cornell.edu" in email or "arxiv.org" in email:
                continue
            new_password = generate_random_password()
            print(f"{email},{new_password}", file=creds_file)
            cursor.execute(
                "UPDATE tapir_users_password SET password_enc = %s WHERE user_id = %s", (hash_password(new_password), user_id)
            )
            sofar += 1
            if sofar >= count:
                break

    # Commit the transaction to save changes
    connection.commit()

    # Close the cursor and connection
    cursor.close()
    connection.close()

    print(f"Updated password for {sofar} users.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('database', type=str, help="Database connection string")
    parser.add_argument('start_user_id', type=int)
    parser.add_argument('count', type=int)

    args = parser.parse_args()
    hack_creds(args.database, args.start_user_id, args.count)


if __name__ == '__main__':
    main()