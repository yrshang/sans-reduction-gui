if [[ -z "$CONFIG" ]]; then
    python -m $INSTRUMENT --galaxy-history-id $HISTORY_ID --host 0.0.0.0 --server timeout=0 --staff-input-file /default_config.py
else
    python -m $INSTRUMENT --galaxy-history-id $HISTORY_ID --host 0.0.0.0 --server timeout=0 --staff-input-file $CONFIG
fi
