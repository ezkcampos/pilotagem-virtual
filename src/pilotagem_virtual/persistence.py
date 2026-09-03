"""Local, transactional snapshots. No network or installation-directory writes."""
import hashlib
import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from pilotagem_virtual.domain.calibration import profile_from_dict


class TrainingStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db=self.connect()
        try:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version > 1:
                raise ValueError('Banco criado por uma versão mais recente')
            db.execute('CREATE TABLE IF NOT EXISTS profiles (device_key TEXT PRIMARY KEY, revision INTEGER NOT NULL, payload TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS attempts (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL)')
            db.execute('PRAGMA user_version=1')
            db.commit()
        finally: db.close()

    def connect(self):
        return sqlite3.connect(self.path, timeout=.1)

    def _fetchone(self, sql, args):
        db=self.connect()
        try: return db.execute(sql,args).fetchone()
        finally: db.close()

    @staticmethod
    def key(info):
        if not info.guid:
            raise ValueError('GUID indisponível; o perfil não pode ser reutilizado')
        return f'{info.guid}:{info.axis_count}'

    def load_profile(self, info):
        row = self._fetchone('SELECT payload FROM profiles WHERE device_key=?',(self.key(info),))
        if not row:
            return None
        profile=profile_from_dict(json.loads(row[0]))
        if profile.device_guid != info.guid or any(p.axis >= info.axis_count for p in (profile.steering,profile.accelerator,profile.brake)):
            raise ValueError('Perfil incompatível')
        return profile

    def save_profile(self, info, profile):
        payload=json.dumps(asdict(profile),allow_nan=False)
        profile_from_dict(json.loads(payload))
        db=self.connect()
        try:
            db.execute('INSERT INTO profiles VALUES (?,1,?) ON CONFLICT(device_key) DO UPDATE SET revision=revision+1,payload=excluded.payload', (self.key(info),payload))
            db.commit()
        finally: db.close()

    def save_attempt(self, payload):
        text=json.dumps(payload,ensure_ascii=False,allow_nan=False,separators=(',',':'))
        previous=self._fetchone('SELECT payload FROM attempts WHERE id=?',(payload['attempt_id'],))
        db=self.connect()
        try:
            if previous and previous[0] != text:
                raise ValueError('Uma tentativa salva não pode ser modificada')
            db.execute('INSERT OR IGNORE INTO attempts VALUES (?,?,?)',(payload['attempt_id'],datetime.now(timezone.utc).isoformat(),text))
            db.commit()
        finally: db.close()


def attempt_payload(snapshot, exercise, report, mode, surface, abs_enabled, comparison_id):
    scenario=asdict(exercise) if exercise else asdict(snapshot.scenario)
    encoded=json.dumps(scenario,sort_keys=True,allow_nan=False)
    return {'schema_version':1,'development_version':'0.2.0-dev','attempt_id':snapshot.attempt_id,
            'snapshot':asdict(snapshot),'exercise':scenario,'scenario_sha256':hashlib.sha256(encoded.encode()).hexdigest(),
            'mode':mode,'surface':surface,'abs_enabled':abs_enabled,'comparison_id':comparison_id,'result':report}
