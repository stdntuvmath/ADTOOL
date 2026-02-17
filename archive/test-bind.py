import json
from ldap3 import Server, Connection, ALL, MODIFY_ADD

# Load credentials
with open("credentials.json") as f:
    creds = json.load(f)

DC_IP = creds["dc_ip"]
USERNAME = creds["username"]
PASSWORD = creds["password"]

server = Server(DC_IP, get_info=ALL)
conn = Connection(server, user=USERNAME, password=PASSWORD)

if not conn.bind():
    print("Bind failed.")
    print(conn.result)
    exit()

print("Bind successful.")

# ---- CONFIG ----
new_username = "Jack.Reacher"
new_password = PASSWORD   # Must meet domain complexity
target_group = "Python-Test-Group"
# ----------------

# 1️⃣ Define new user DN
user_dn = f"CN=Jack Reacher,CN=Users,DC=lab,DC=local"

# 2️⃣ Create user
conn.add(
    user_dn,
    ["top", "person", "organizationalPerson", "user"],
    {
        "sAMAccountName": new_username,
        "userPrincipalName": f"{new_username}@lab.local",
        "givenName": "Jack",
        "sn": "Reacher",
        "displayName": "Jack Reacher"
    }
)

if conn.result["result"] == 0:
    print("User created successfully.")
else:
    print("User creation failed.")
    print(conn.result)
    conn.unbind()
    exit()

# 3️⃣ Set password
conn.extend.microsoft.modify_password(user_dn, new_password)

# 4️⃣ Enable account (512 = NORMAL_ACCOUNT)
conn.modify(user_dn, {"userAccountControl": [("MODIFY_REPLACE", [512])]})

print("Password set and account enabled.")

# 5️⃣ Find group DN
conn.search(
    search_base="DC=lab,DC=local",
    search_filter=f"(sAMAccountName={target_group})",
    attributes=["distinguishedName"]
)

if not conn.entries:
    print("Group not found.")
    conn.unbind()
    exit()

group_dn = conn.entries[0].distinguishedName.value

# 6️⃣ Add user to group
conn.modify(
    group_dn,
    {"member": [(MODIFY_ADD, [user_dn])]}
)

if conn.result["result"] == 0:
    print("User added to group successfully.")
else:
    print("Failed to add user to group.")
    print(conn.result)

conn.unbind()

# #search_filter='(objectClass=user)', # This will include ALL accounts
# #search_filter='(&(objectClass=user)(!(objectClass=computer)))',# Exclude computer accounts
        