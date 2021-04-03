import sqlite3

conn = sqlite3.connect('covid-stats.db')
print('database opened successfully')
conn.execute("""create table access (
    access_id integer primary key,
    access_type text not null
    )""")
print('table access created successfully')

conn.execute("""create table users (
    id integer primary key autoincrement,
    user_name text not null,
    country text not null,
    password text not null,
    access_id integer default 2,
  constraint fk_access
    foreign key (access_id)
    references access(access_id)
    )""")
print('table users created successfully')

conn.execute("""insert into access values(1, 'admin' );""")
conn.execute("""insert into access values(2, 'user' );""")
conn.commit()