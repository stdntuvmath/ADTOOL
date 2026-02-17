import sys
import json
from ldap3 import Server, Connection, ALL, MODIFY_ADD, MODIFY_DELETE
import logging
from pathlib import Path

# ---- Logging Setup ----
LOG_DIR = Path.home() / "adtool_logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "adtool.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger()


# ---- Load credentials ----
with open("credentials.json") as f:
    creds = json.load(f)

DC_IP = creds["dc_ip"]
USERNAME = creds["username"]
PASSWORD = creds["password"]

BASE_DN = "DC=lab,DC=local"
USERS_DN = "CN=Users," + BASE_DN



# Connect to AD and return the connection object

def connect():
    server = Server(DC_IP, get_info=ALL)
    conn = Connection(server, user=USERNAME, password=PASSWORD)
    if not conn.bind():
        print("Bind failed.")
        print(conn.result)
        sys.exit()
    return conn





# Create a new user with the given username (format: First.Last)

def create_user(conn, username):

    try:
        # ensure we have the right number of arguments
        if len(sys.argv) < 3:
            print("Usage: python adtool.py create-user First.Last")
            sys.exit()

        first, last = username.split(".")
        display_name = f"{first} {last}"
        user_dn = f"CN={display_name},{USERS_DN}"

        conn.search(
        BASE_DN,
        f"(sAMAccountName={username})",
        attributes=["sAMAccountName"]
    )

        if conn.entries:
            print("User already exists.")
            return

        conn.add(
            user_dn,
            ["top", "person", "organizationalPerson", "user"],
            {
                "sAMAccountName": username,
                "userPrincipalName": f"{username}@lab.local",
                "givenName": first,
                "sn": last,
                "displayName": display_name,
            }
        )

        if conn.result["result"] != 0:
            print("User creation failed.")
            print(conn.result)
            return

        # Set user password
        newPassword = input(f"Enter password for {username} (must meet domain complexity): ")
        conn.extend.microsoft.modify_password(user_dn, newPassword)
        conn.modify(user_dn, {"userAccountControl": [("MODIFY_REPLACE", [512])]})

        logger.info(f"User created and enabled: {username}")
        print(f"User {username} created and enabled.")

    except Exception as e:
        logger.exception(f"Unexpected error in create_user for {username}")
        print("Unexpected error occurred. Check log file.")

# Create a new group with the given name
def create_group(conn, group_name):

    try:
        # ensure we have the right number of arguments
        if len(sys.argv) < 3:
            print("Usage: python adtool.py create-group GroupName")
            sys.exit()

        group_dn = f"CN={group_name},{USERS_DN}"
        conn.add(group_dn, ["top", "group"], {"sAMAccountName": group_name})

        if conn.result["result"] == 0:
            print(f"Group {group_name} created successfully.")
        else:
            print("Group creation failed.")
            print(conn.result)

    except Exception as e:
        logger.exception(f"Unexpected error in create_group for {group_name}")
        print("Unexpected error occurred. Check log file.")

# Add a user to a group
def add_user_to_group(conn, username, group_name):

    try:
        # ensure we have the right number of arguments
        if len(sys.argv) < 4:
            print("Usage: python adtool.py add-user-to-group First.Last GroupName")
            sys.exit()

        # Get user DN
        conn.search(
            BASE_DN,
            f"(sAMAccountName={username})",
            attributes=["distinguishedName"]
        )

        if not conn.entries:
            print("User not found.")
            return

        user_dn = conn.entries[0].distinguishedName.value

        # Get group DN
        conn.search(
            BASE_DN,
            f"(sAMAccountName={group_name})",
            attributes=["distinguishedName"]
        )

        if not conn.entries:
            print("Group not found.")
            return

        group_dn = conn.entries[0].distinguishedName.value

        # Add membership
        conn.modify(
            group_dn,
            {"member": [(MODIFY_ADD, [user_dn])]}
        )

        if conn.result["result"] == 0:
            print(f"{username} added to {group_name}.")
        else:
            print("Failed to add user to group.")
            print(conn.result)

    except Exception as e:
        logger.exception(f"Unexpected error in add_user_to_group for {username} in group {group_name}")
        print("Unexpected error occurred. Check log file.")

# Remove a user from a group
def delete_user_from_group(conn, username, group_name):

    try:
        # ensure we have the right number of arguments
        if len(sys.argv) < 4:
            print("Usage: python adtool.py delete-user-from-group First.Last GroupName")
            sys.exit()

        # Get user DN
        conn.search(
            BASE_DN,
            f"(sAMAccountName={username})",
            attributes=["distinguishedName"]
        )

        if not conn.entries:
            print("User not found.")
            return

        user_dn = conn.entries[0].distinguishedName.value

        # Get group DN
        conn.search(
            BASE_DN,
            f"(sAMAccountName={group_name})",
            attributes=["distinguishedName"]
        )

        if not conn.entries:
            print("Group not found.")
            return

        group_dn = conn.entries[0].distinguishedName.value

        # Remove membership
        conn.modify(
            group_dn,
            {"member": [(MODIFY_DELETE, [user_dn])]}
        )

        if conn.result["result"] == 0:
            print(f"{username} removed from {group_name}.")
        else:
            print("Failed to remove from group.")
            print(conn.result)
    except Exception as e:
        logger.exception(f"Unexpected error in delete_user_from_group for {username} from group {group_name}")
        print("Unexpected error occurred. Check log file.")

# List all users in a group
def list_users_in_group(conn, group_name):

    try:
        # ensure we have the right number of arguments
        if len(sys.argv) < 3:
            print("Usage: python adtool.py list-users-in-group GroupName")
            sys.exit()

        conn.search(
            BASE_DN,
            f"(memberOf=CN={group_name},{USERS_DN})",
            attributes=["sAMAccountName"]
        )

        print("\nUsers:")
        for entry in conn.entries:
            print(entry.sAMAccountName)

    except Exception as e:
        logger.exception(f"Unexpected error in list_users_in_group for group {group_name}")
        print("Unexpected error occurred. Check log file.")

# enable user
def enable_user(conn, username):
    try:
        # ensure we have the right number of arguments
        if len(sys.argv) < 3:
            print("Usage: python adtool.py enable-user First.Last")
            sys.exit()

        ACCOUNTDISABLE = 2

        logger.info(f"Attempting to enable user: {username}")

        conn.search(
            BASE_DN,
            f"(sAMAccountName={username})",
            attributes=["distinguishedName", "userAccountControl"]
        )

        if not conn.entries:
            logger.warning(f"User not found: {username}")
            print("User not found.")
            return

        user_dn = conn.entries[0].distinguishedName.value
        current_uac = int(conn.entries[0].userAccountControl.value)

        # Remove disable bit
        new_uac = current_uac & ~ACCOUNTDISABLE

        conn.modify(user_dn, {
            "userAccountControl": [("MODIFY_REPLACE", [new_uac])]
        })

        if conn.result["result"] == 0:
            logger.info(f"User enabled: {username}")
            print(f"{username} enabled.")
        else:
            logger.error(f"Failed to enable user: {conn.result}")
            print("Failed to enable user.")

    except Exception:
        logger.exception(f"Unexpected error in enable_user for {username}")
        print("Unexpected error occurred. Check log file.")

# disable user
def disable_user(conn, username):
    try:
        # Argument length check
        if len(sys.argv) < 3:
            print("Usage: adtool disable-user First.Last")
            logger.warning("disable-user called with insufficient arguments")
            sys.exit()

        ACCOUNTDISABLE = 2

        logger.info(f"Attempting to disable user: {username}")

        # Lookup user
        conn.search(
            BASE_DN,
            f"(sAMAccountName={username})",
            attributes=["distinguishedName", "userAccountControl"]
        )

        if not conn.entries:
            logger.warning(f"User not found: {username}")
            print("User not found.")
            return

        user_dn = conn.entries[0].distinguishedName.value
        current_uac = int(conn.entries[0].userAccountControl.value)

        # Set disable bit
        new_uac = current_uac | ACCOUNTDISABLE

        conn.modify(
            user_dn,
            {"userAccountControl": [("MODIFY_REPLACE", [new_uac])]}
        )

        if conn.result["result"] == 0:
            logger.info(f"User disabled successfully: {username}")
            print(f"{username} disabled.")
        else:
            logger.error(f"Failed to disable user: {conn.result}")
            print("Failed to disable user.")

    except Exception:
        logger.exception(f"Unexpected error in disable_user for {username}")
        print("Unexpected error occurred. Check log file.")

# ---- CLI Logic ----
def main():

    try:
        if len(sys.argv) < 2:
            print("Usage: adtool <command>")
            print("Please pick from the commands below:")
            print()
            print("  create-user First.Last")
            print("  add-user-to-group First.Last GroupName")
            print("  create-group GroupName")
            print("  delete-user-from-group First.Last GroupName")
            print("  list-users-in-group GroupName")
            print("  enable-user First.Last")
            print("  disable-user First.Last")
            sys.exit()
        

        command = sys.argv[1]

        conn = connect()

        if command == "create-user":
            username = sys.argv[2]
            create_user(conn, username)

        elif command == "add-user-to-group":
            username = sys.argv[2]
            group = sys.argv[3]
            add_user_to_group(conn, username, group)

        elif command == "create-group":
            group_name = sys.argv[2]
            create_group(conn, group_name)

        elif command == "delete-user-from-group":
            username = sys.argv[2]
            group = sys.argv[3]
            delete_user_from_group(conn, username, group)

        elif command == "list-users-in-group":
            group_name = sys.argv[2]
            list_users_in_group(conn, group_name)

        elif command == "enable-user":
            username = sys.argv[2]
            enable_user(conn, username)

        elif command == "disable-user":
            username = sys.argv[2]
            disable_user(conn, username)

        else:
            print("Unknown command. Please pick from the commands below:")
            print("  python adtool.py create-user First.Last")
            print("  python adtool.py add-user-to-group First.Last GroupName")
            print("  python adtool.py create-group GroupName")
            print("  python adtool.py delete-user-from-group First.Last GroupName")
            print("  python adtool.py list-users-in-group GroupName")
            print("  python adtool.py enable-user First.Last")
            print("  python adtool.py disable-user First.Last")

        
        conn.unbind()
        logging.shutdown()
    except Exception:
        logger.exception("Fatal error in main()")
        print("Fatal error occurred. Check log file.")

    finally:
        if conn:
            try:
                conn.unbind()
            except:
                pass
        logging.shutdown()

if __name__ == "__main__":
    main()



