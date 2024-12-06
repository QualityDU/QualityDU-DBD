Note: requires pdftotext and redis to be available on the host system


## Deployment
It's recommended to run each python script in separate tmux session.

Example deploy scripts:

1. start.sh
```bash
#!/bin/bash

QDU_DUSCR_IM_SESS="qdu_dim";
QDU_DBD_ACTS_PDF_CONSUMER_SESS="qdu_dbdap";
QDU_DBD_ACTS_TXT_CONSUMER_SESS="qdu_dbdat";
QDU_DBD_KEYWORDING_CONSUMER_SESS="qdu_kw";

echo "@@@ start.sh - the QDU Spawner (deploy script) @@@";

echo "QDU Spawner - defensively deleting possible orphaned message queues from redis";
redis-cli del duscr:file_mq;
redis-cli del qualitydu_dbd:file_mq;
redis-cli del qualitydu_dbd:keybert_file_mq;

# Note: If you want to start from empty database, we assume that you empty the acts table and delete/empty the ACTS_PDF dir and empty the ACTS_TXT dir manualy

# uruchomienie bash duscr-im.sh - pobiera pliki PDF
echo "QDU Spawner - creating QDU_DUSCR_IM_SESS";
tmux new-session -ds $QDU_DUSCR_IM_SESS;
tmux send-keys -t $QDU_DUSCR_IM_SESS C-m C-m C-m 'bash' C-m 'echo "Initial scrap started: $(date)" >> /home/user/deploys/duscr/duscr-im.log' C-m '/home/user/repos/duscr-im-container/duscr/duscr-im.sh /home/user/deploys/duscr/ACTS-PDF &>> /home/user/deploys/duscr/duscr-im.log' C-m C-m C-m 'echo "Initial scrap ended: $(date)" >> /home/user/deploys/duscr/duscr-im.log' C-m C-m &

#uruchomienie python acts_pdf_consumer.py - generuje pliki txt
echo "QDU Spawner - creating QDU_DBD_ACTS_PDF_CONSUMER_SESS";
tmux new-session -ds $QDU_DBD_ACTS_PDF_CONSUMER_SESS;
tmux send-keys -t $QDU_DBD_ACTS_PDF_CONSUMER_SESS C-m C-m C-m 'bash' C-m 'cd /home/user/repos/QualityDU-DBD' C-m 'source v/bin/activate' C-m C-m 'python acts_pdf_consumer.py' C-m C-m &

#uruchomienie python acts_txt_consumer.py - zapisuje dane o aktach do bazy
echo "QDU Spawner - creating QDU_DBD_ACTS_TXT_CONSUMER_SESS";
tmux new-session -ds $QDU_DBD_ACTS_TXT_CONSUMER_SESS;
tmux send-keys -t $QDU_DBD_ACTS_TXT_CONSUMER_SESS C-m C-m C-m 'bash' C-m 'cd /home/user/repos/QualityDU-DBD' C-m 'source v/bin/activate' C-m C-m 'python acts_txt_consumer.py' C-m C-m &

#uruchomienie python keywording_consumer.py - wyznacza słowa kluczowe i zapisuje do bazy danych
echo "QDU Spawner - creating QDU_DBD_KEYWORDING_SESS";
tmux new-session -ds $QDU_DBD_KEYWORDING_CONSUMER_SESS;
tmux send-keys -t $QDU_DBD_KEYWORDING_CONSUMER_SESS C-m C-m C-m 'bash' C-m 'cd /home/user/repos/QualityDU-DBD' C-m 'source v/bin/activate' C-m C-m 'python keywording_consumer.py' C-m C-m &

echo "QDU Spawner: waiting for tmux sessions";
wait;
echo "@@@ QDU Spawner: exit script @@@";
```

2. cron.sh
```bash
#!/bin/bash

echo "Sync check start: $(date)" >> /home/user/deploys/duscr/duscr-im.log;
~/repos/duscr-im-container/duscr/duscr-im.sh /home/user/deploys/duscr/ACTS-PDF &>> /home/user/deploys/duscr/duscr-im.log;
echo "Sync check end: $(date)" >> /home/user/deploys/duscr/duscr-im.log;
```
Note: cron.sh should be added to crontab only after the initial scrap is done. (check in duscr-im.log)<br>
Note: The start.sh script can be launched in tmux session qdu_spawn / qdu_launch / custom name

## Architecture
![image](https://github.com/user-attachments/assets/d1b591e4-e262-494b-b0eb-f958a794596b)
## Architecture including full system
![image](https://github.com/user-attachments/assets/5723a9e7-54ed-485e-9e3c-a3dee112d4b7)

## duscr-im
Duscr-im, the DU path scraper can be found in a separate repository in the QualityDU org. See here: https://github.com/QualityDU/duscr/blob/path-scraper/duscr-im.sh
