#!/bin/sh

flask db init
sleep 0.5
flask db migrate
sleep 1
flask db upgrade

exec flask run --host=0.0.0.0