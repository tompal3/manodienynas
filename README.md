# Manodienynas

It's a tool to scrape manodienynas.lt and forward email messages for new events.


## Configuration 

`config.json` is file where client takes configuration variables, rename `example.config.json`  

- [username] - manodienynas.lt email address that you login with
- [password] - your private manodienynas.lt password 
- [uri] - "https://www.manodienynas.lt" default, no need to change, unless domain changes
- [sender_email] - email address that will be forwarding your messages
- [receiver_email] - email address to whom you want to forward your messages
- [smtp_server] - your smtp servers fqdn address, by default working on tcp 25 port.
- [events_file] - file where to store events history, so that only new ones are forwarded

## How to run it 

clone this repo

Install dependencies

```sh
pip3 install -r requirements.txt
```

Setup crontab

```sh
crontab -e
```

add a line:

```sh
30 * * * * /bin/python3  ~/manodienynas/diary.py
```

~/manodienynas/diary.py should point to `diary.py` file and cron service should be enabled.

## TO DO 

- need to add logs
- smtp with tls and auth
