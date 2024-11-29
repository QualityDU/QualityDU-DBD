import redis
from datetime import datetime
import psycopg2
import os
from dotenv import load_dotenv
import subprocess

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

'''
The acts table is defined as:
CREATE TABLE public.acts (
	du_code varchar NOT NULL,
	"year" int4 NOT NULL,
	journal_no int4 DEFAULT 0 NOT NULL,
	num_edits int4 DEFAULT 0 NOT NULL,
	text_payload varchar NOT NULL,
	date_scraped date NOT NULL,
	act_id serial4 NOT NULL,
	last_edited_date date NULL,
	last_tag_added_date date NULL,
	"position" int4 DEFAULT 0 NOT NULL,
	part_no int4 DEFAULT 0 NOT NULL,
	CONSTRAINT acts_pk PRIMARY KEY (act_id)
);
'''
def txt_consume(txt_path, conn, cur):
  if not os.path.isfile(txt_path):
    return;

  txt_basename = os.path.basename(txt_path)
  try:
    with open(txt_path, 'r') as txt_file:
      txt_payload = txt_file.read()
      # the basename has the format D<YYYY><JJJ><PPPP><TT>.txt
      # where YYYY is the year, JJJ is the journal number, PPPP is act position, and TT is part number
      
      # du_code is D<YYYY><JJJ><PPPP><TT>
      du_code = txt_basename.split('.')[0]

      # year is YYYY
      year = int(du_code[1:5])

      # journal_no is JJJ
      journal_no = int(du_code[5:8])

      # postion is PPPP
      position = int(du_code[8:12])

      # part_no is TT
      part_no = int(du_code[12:14])

      cur.execute(
        '''
        INSERT INTO acts (du_code, year, journal_no, position, part_no, text_payload, date_scraped)
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
        ''',
        (du_code, year, journal_no, position, part_no, txt_payload)
      )
      conn.commit() # ddl statements need to be committed
      # push to qualitydu_dbd:keybert_file_mq
      subprocess.run(["redis-cli", "rpush", "qualitydu_dbd:keybert_file_mq", f"{txt_basename}"])
  except Exception as e:
    print(f"Error processing {txt_path}: {e}")
    # repush to the queue
    subprocess.run(["redis-cli", "rpush", "qualitydu_dbd:file_mq", f"{txt_basename}"])

if __name__ == '__main__':
  load_dotenv()
  with psycopg2.connect(os.getenv("DB_CONN")) as conn:
    with conn.cursor() as cur:
      while True:
        # the mq contains pdf file basename list
        message = redis_client.blpop('qualitydu_dbd:file_mq', timeout=0)
        if message:
          txt_basename = message[1].decode('utf-8')
          if not txt_basename:
            raise Exception('Failed to read message[1]')
          print(f"Reading {txt_basename}")
          txt_path = os.path.join(os.getenv('ACTS_TXT_DIR'), txt_basename)
          txt_consume(txt_path, conn, cur)
        else:
            raise Exception('BLPOP returned a falsy value')
