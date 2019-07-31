#!/usr/bin/python
import psycopg2
import datetime
import json
import decimal
from bcreg.config import config
from bcreg.eventprocessor import EventProcessor


with EventProcessor() as event_processor:
    # run this query against Event Processor database:
    sql1a = "select COALESCE(MAX(LAST_CORP_HISTORY_ID), 0) from CORP_AUDIT_LOG"
    sql2 = """
    SELECT record_id, system_type_cd, corp_num, corp_state, corp_json->>'corp_typ_cd' as corp_typ_cd, last_event->>'event_id' as last_event_id, last_event->>'event_date' as last_event_date, entry_date, process_date, process_msg 
    FROM corp_history_log
    WHERE record_id > %s AND process_date is not null
    ORDER BY record_id;
    """
    print("Get corp history processed rec id", datetime.datetime.now())
    event_proc_inbound_recid = event_processor.get_event_proc_sql("inbound_recid", sql1a)
    print("Get corp history from Event Processor DB", datetime.datetime.now())
    event_proc_inbound_recs = event_processor.get_event_proc_sql("inbound_recs", sql2, (event_proc_inbound_recid[0]['coalesce'],))
    print("... build audit log", datetime.datetime.now())
    i = 0
    for inbound_rec in event_proc_inbound_recs:
        i = i + 1
        if (i % 10000 == 0):
            print('>>> Processing {} {}.'.format(i, datetime.datetime.now()))

        if inbound_rec['process_msg'] and inbound_rec['process_msg'] == 'Withdrawn':
            # skip
            pass
        else:
            # see if we have a record for this corp yet
            sql2a = """
            SELECT RECORD_ID, LAST_CORP_HISTORY_ID, SYSTEM_TYPE_CD, LAST_EVENT_DATE, CORP_NUM, CORP_STATE, CORP_TYPE, ENTRY_DATE
            FROM CORP_AUDIT_LOG WHERE CORP_NUM = %s;
            """
            corp_recs = event_processor.get_event_proc_sql("corp_recs", sql2a, (inbound_rec['corp_num'],))
            if 0 == len(corp_recs):
                # if not, add it
                sql2b = """
                INSERT INTO CORP_AUDIT_LOG 
                (LAST_CORP_HISTORY_ID, SYSTEM_TYPE_CD, LAST_EVENT_DATE, CORP_NUM, CORP_STATE, CORP_TYPE, ENTRY_DATE)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING RECORD_ID;
                """
                cur = None
                try:
                    cur = event_processor.conn.cursor()
                    cur.execute(sql2b, (inbound_rec['record_id'], inbound_rec['system_type_cd'], inbound_rec['last_event_date'], inbound_rec['corp_num'], inbound_rec['corp_state'], inbound_rec['corp_typ_cd'], datetime.datetime.now(),))
                    _record_id = cur.fetchone()[0]
                    event_processor.conn.commit()
                    cur.close()
                    cur = None
                except (Exception, psycopg2.DatabaseError) as error:
                    print(error)
                    raise
                finally:
                    if cur is not None:
                        cur.close()
            else:
                # if yes, see if we need to update it
                sql2c = """
                UPDATE CORP_AUDIT_LOG
                SET LAST_CORP_HISTORY_ID = %s, LAST_EVENT_DATE = %s, CORP_STATE = %s, CORP_TYPE = %s, ENTRY_DATE = %s
                WHERE RECORD_ID = %s AND CORP_NUM = %s;
                """
                cur = None
                corp_rec = corp_recs[0]
                try:
                    cur = event_processor.conn.cursor()
                    cur.execute(sql2c, (inbound_rec['record_id'], inbound_rec['last_event_date'], inbound_rec['corp_state'], inbound_rec['corp_typ_cd'], datetime.datetime.now(), corp_rec['record_id'], corp_rec['corp_num'],))
                    event_processor.conn.commit()
                    cur.close()
                    cur = None
                except (Exception, psycopg2.DatabaseError) as error:
                    print(error)
                    raise
                finally:
                    if cur is not None:
                        cur.close()

with EventProcessor() as event_processor:
    # run this query against Event Processor database:
    sql1b = "select COALESCE(MAX(LAST_CREDENTIAL_ID), 0) from CORP_AUDIT_LOG where corp_state = 'ACT'"
    sql1c = "select COALESCE(MAX(LAST_CREDENTIAL_ID), 0) from CORP_AUDIT_LOG where corp_state = 'HIS'"
    sql3s = [
    """
    SELECT record_id, corp_num, credential_json->>'entity_status' as corp_state, credential_json->>'entity_type' as corp_typ_cd, credential_json->>'effective_date' as effective_date, entry_date, process_date 
    FROM credential_log 
    WHERE process_date is not null and credential_type_cd = 'REG'
      AND ((corp_state = 'ACT' and record_id > %s) OR  (corp_state = 'HIS' and record_id > %s))
    ORDER BY record_id;
    """,
    """
    SELECT record_id, corp_num, credential_json->>'entity_status' as corp_state, credential_json->>'entity_type' as corp_typ_cd, credential_json->>'effective_date' as effective_date, entry_date, process_date 
    FROM credential_log 
    WHERE process_date is not null and credential_type_cd = 'REG'
      AND corp_num in (select corp_num from CORP_AUDIT_LOG where last_credential_id is null)
    ORDER BY record_id;
    """,
    ]

    print("Get corp REG processed rec ids", datetime.datetime.now())
    event_proc_outbound_act_recid = event_processor.get_event_proc_sql("outbound_act_recid", sql1b)
    event_proc_outbound_his_recid = event_processor.get_event_proc_sql("outbound_his_recid", sql1c)
    print("Get corp REG credentials from Event Processor DB", datetime.datetime.now())
    for sql3 in sql3s:
        event_proc_outbound_recs = event_processor.get_event_proc_sql("outbound_recs", sql3, (event_proc_outbound_act_recid[0]['coalesce'], event_proc_outbound_his_recid[0]['coalesce'],))
        print("... build audit log", datetime.datetime.now())
        i = 0
        for outbound_rec in event_proc_outbound_recs:
            i = i + 1
            if (i % 10000 == 0):
                print('>>> Processing {} {}.'.format(i, datetime.datetime.now()))
            # see if we have a record for this corp yet
            sql3a = """
            SELECT RECORD_ID, LAST_CORP_HISTORY_ID, SYSTEM_TYPE_CD, LAST_EVENT_DATE, CORP_NUM, CORP_STATE, CORP_TYPE, ENTRY_DATE,
                    LAST_CREDENTIAL_ID, CRED_EFFECTIVE_DATE
            FROM CORP_AUDIT_LOG WHERE CORP_NUM = %s;
            """
            corp_recs = event_processor.get_event_proc_sql("corp_recs", sql3a, (outbound_rec['corp_num'],))
            if 0 == len(corp_recs):
                # if not, it's an error
                # ignore for now
                print("Error no inbound record found for", outbound_rec['corp_num'])
                pass
            else:
                # if yes, see if we need to update it
                sql3b = """
                UPDATE CORP_AUDIT_LOG
                SET LAST_CREDENTIAL_ID = %s, CRED_EFFECTIVE_DATE = %s
                WHERE RECORD_ID = %s AND CORP_NUM = %s;
                """
                cur = None
                corp_rec = corp_recs[0]
                try:
                    cur = event_processor.conn.cursor()
                    cur.execute(sql3b, (outbound_rec['record_id'], outbound_rec['effective_date'], corp_rec['record_id'], corp_rec['corp_num']))
                    event_processor.conn.commit()
                    cur.close()
                    cur = None
                except (Exception, psycopg2.DatabaseError) as error:
                    print(error)
                    raise
                finally:
                    if cur is not None:
                        cur.close()

print("Got all corp audits", datetime.datetime.now())

