import redis
from datetime import datetime
import psycopg2
import os
from dotenv import load_dotenv
import subprocess

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

def pdf_consume(pdf_name, pdf_dir, txt_dir):
  # call pdftotext to extract text from pdf
  process_pdftotext = subprocess.Popen(
    [
      "pdftotext", 
      #'"' + f"{pdf_dir}/{pdf_name}.pdf" + '"', 
      os.path.join(pdf_dir, f"{pdf_name}.pdf"),
      #f"{txt_dir}/{pdf_name}.txt"
      os.path.join(txt_dir, f"{pdf_name}.txt")
    ]
  )
  process_pdftotext.wait()
  # push to qualitydu_dbd:file_mq
  subprocess.run(["redis-cli", "rpush", "qualitydu_dbd:file_mq", f"{pdf_name}.txt"])

if __name__ == '__main__':
  load_dotenv()
  while True:
    # the mq contains pdf file basename list
    message = redis_client.blpop('duscr:file_mq', timeout=0)
    if message:
      pdf_basename = message[1].decode('utf-8')
      if not pdf_basename:
        raise Exception('Failed to read message[1]')
      print(f"Processing {pdf_basename}")
      pdf_name = pdf_basename.split('.')[0]
      pdf_consume(pdf_name, os.getenv('ACTS_PDF_DIR'), os.getenv('ACTS_TXT_DIR'))
    else:
      raise Exception('BLPOP returned a falsy value')