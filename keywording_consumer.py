import redis
from datetime import datetime
import psycopg2
import os
from dotenv import load_dotenv
import subprocess
from keybert import KeyBERT

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
kw_model = KeyBERT()

'''
The tags table is defined as:
CREATE TABLE public.tags (
	tag_id serial4 NOT NULL,
	"name" varchar NOT NULL,
	num_assigned int4 DEFAULT 0 NOT NULL,
	creator_id int4 NULL,
	date_created date NOT NULL,
	last_assigned_date date NULL,
	CONSTRAINT tags_pk PRIMARY KEY (tag_id),
	CONSTRAINT tags_unique UNIQUE (name),
	CONSTRAINT "creator_id_FK" FOREIGN KEY (creator_id) REFERENCES public.users(user_id)
);

The acts_tags table is defined as:
CREATE TABLE public.acts_tags (
	id serial4 NOT NULL,
	act_id int4 NOT NULL,
	tag_id int4 NOT NULL,
	assigned_date date NOT NULL,
	assigner_id int4 NULL,
	CONSTRAINT acts_tags_pk PRIMARY KEY (id),
	CONSTRAINT "act_id_FK" FOREIGN KEY (act_id) REFERENCES public.acts(act_id),
	CONSTRAINT "assigner_id_FK" FOREIGN KEY (assigner_id) REFERENCES public.users(user_id),
	CONSTRAINT "tag_id_FK" FOREIGN KEY (tag_id) REFERENCES public.tags(tag_id)
);

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
def txt_keywording_consume(txt_path, conn, cur):
  try:
    with open(txt_path , 'r') as txt_file:
      txt_payload = txt_file.read()
      keywords = kw_model.extract_keywords(txt_payload)
      for keyword in keywords:
        tag = keyword[0]
        # score = keyword[1]
        # if score < 0.1:
        #   break

        # check if tag exists
        cur.execute(
          '''
          SELECT tag_id FROM tags WHERE "name" = %s
          ''',
          (tag,)
        )
        tag_id = cur.fetchone()
        if tag_id:
          tag_id = tag_id[0]
        else:
          cur.execute(
            '''
            INSERT INTO tags ("name", num_assigned, date_created)
            VALUES (%s, 0, NOW())
            RETURNING tag_id
            ''',
            (tag,)
          )
          tag_id = cur.fetchone()[0]
        # increase num_assigned
        cur.execute(
          '''
          UPDATE tags
          SET num_assigned = num_assigned + 1
          WHERE tag_id = %s
          ''',
          (tag_id,)
        )
        # obtain act_id
        du_code = os.path.basename(txt_path).split('.')[0]
        act_id = None
        cur.execute(
          '''
          SELECT act_id FROM acts WHERE du_code = %s
          ''',
          (du_code,)
        )
        row = cur.fetchone()
        if row:
          act_id = row[0]
        else:
          raise Exception(f"act_id not found for {du_code}")
        # insert into acts_tags
        cur.execute(
          '''
          INSERT INTO acts_tags (act_id, tag_id, assigned_date)
          VALUES (%s, %s, NOW())
          ''',
          (act_id, tag_id)
        )
        # update last_tag_added_date
        cur.execute(
          '''
          UPDATE acts
          SET last_tag_added_date = NOW()
          WHERE act_id = %s
          ''',
          (act_id,)
        )
        conn.commit() # finalize transaction
  except Exception as e:
    print(f"Error processing {txt_path}: {e}")
    # repush to the queue
    subprocess.run(["redis-cli", "rpush", "qualitydu_dbd:keybert_file_mq", f"{os.path.basename(txt_path)}"])

if __name__ == '__main__':
  load_dotenv()
  with psycopg2.connect(os.getenv("DB_CONN")) as conn:
    with conn.cursor() as cur:
      while True:
        # the mq contains pdf file basename list
        message = redis_client.blpop('qualitydu_dbd:keybert_file_mq', timeout=0)
        if message:
          txt_basename = message[1].decode('utf-8')
          if not txt_basename:
            raise Exception('Failed to read message[1]')
          print(f"Reading {txt_basename}")
          txt_path = os.path.join(os.getenv('ACTS_TXT_DIR'), txt_basename)
          txt_keywording_consume(txt_path, conn, cur)
        else:
            raise Exception('BLPOP returned a falsy value')