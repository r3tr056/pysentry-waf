

import datetime
import sqlite3
import json
import os
import pandas as pd

from waf.schema import WAFRequest


class DBController(object):
    def __init__(self) -> None:
        self.conn = sqlite3.connect("log.db")
        self.conn.row_factory = sqlite3.Row

    def save(self, obj):
        if not isinstance(obj, WAFRequest):
            raise TypeError("Object should be a WAFRequest!!!")

        cursor = self.conn.cursor()
        obj.timestamp = datetime.datetime.now()
        cursor.execute("INSERT INTO logs (timestamp, origin, host, method) VALUES (?, ?, ?, ?)", (obj.timestamp, obj.origin, obj.host, obj.method))

        obj.id = cursor.lastrowid

        file_name = str(obj.id) + '.json'
        file_path = os.path.join('requests_log', file_name)

        with open(file_path, 'w') as f:
            json.dump(json.loads(obj.to_json()), f)

        for threat, location in obj.threats.items():
            cursor.execute("INSERT INTO threats (log_id, threat_type, location) VALUES (?, ?, ?)", (obj.id, threat, location))

        self.conn.commit()

    def __create_entry(self, row):
        entry = dict(row)
        entry['Link'] = f"[Review](https://127.0.0.1:8050/review/'{str(entry['id'])})"

        return entry

    def read_all(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM logs AS l JOIN threats AS t ON l.id = t.log_id")
        results = cursor.fetchall()
        data = [self.__create_entry(row) for row in results]
        return pd.DataFrame(data)

    def __create_single_entry(self, row):
        return [row['threat_type'], row['location']]

    def read_request(self, id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM logs AS l JOIN threats AS t ON l.id = t.log_id WHERE l.id = ?", (id, ))
        results = cursor.fetchall()
        log = {}
        if len(results) != 0:
            log['timestamp'] = results[0]['timestamp']
            log['origin'] = results[0]['origin']
            log['host'] = results[0]['host']
            log['method'] = results[0]['method']

        data = [self.__create_single_entry(row) for row in results]

        return log, data

    def close(self):
        self.conn.close()
