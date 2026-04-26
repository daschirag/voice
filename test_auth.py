import httpx

login = httpx.post("http://localhost:8000/api/v1/auth/login", data={
    "username": "atlasAdmin", "password": "admin"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

users = httpx.get("http://localhost:8000/api/v1/admin/users", headers=headers)
print("All users:")
for u in users.json():
    print(f"  {u['username']} | role={u['role']} | verified={u['is_verified']}")

for u in users.json():
    if u["username"] == "testuser":
        v = httpx.put(f"http://localhost:8000/api/v1/admin/verify/{u['id']}", headers=headers)
        print("Verified testuser:", v.json())

stats = httpx.get("http://localhost:8000/api/v1/admin/stats", headers=headers)
print("Stats:", stats.json())