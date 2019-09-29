# Minter node monitoring tool
A python service sending alerts via Telegram bot in case of either your node is offline or has missed a block.

### Prerequisites
1. Your own Telegram bot with api token (create via @BotFather bot)
2. Your own server with Python 3+, pip, virtualenv installed

### Service setup
Execute line by line in server terminal:
```
useradd -m minter-monitoring
chown -R minter-monitoring:minter-monitoring /home/minter-monitoring/
cd /home/minter-monitoring/
virtualenv venv
source venv/bin/activate
pip install python-telegram-bot==12.0.0b1
pip install git+https://github.com/U-node/minter-sdk git+https://github.com/Minterious/minter-monitoring
```
Create `/home/minter-monitoring/config.json` file based on [example](https://github.com/Minterious/minter-monitoring/blob/master/config-example.json).
You should customize the following parameters:
1. `minter_api_url` - API url of a synced mainnet Minter node
2. `minter_nodes_pub_keys` - public keys of nodes to monitor
3. `telegram_bot_token` - Telegram Bot API access token
4. `monitoring_auth_key` - can be any secret string to use as an alerts subscription key for your Telegram bot

Update node-pubkey.json with public key -> node name to beautify notification messages if there is no public key of node you want to monitor.

Create service file like `/etc/systemd/system/minter-monitoring.service` with the following content:
```
[Unit]
After=network.target

[Service]
Type=simple
User=minter-monitoring 
ExecStart=/home/minter-monitoring/venv/bin/python /home/minter-monitoring/venv/lib/python3.6/site-packages/mintermonitoring/main.py /home/minter-monitoring/config.json 
Restart=always
RestartSec=1

[Install]
WantedBy=multi-user.target
Alias=minter-monitoring.service
```

### Usage
After running the service send `/start {monitoring_auth_key}` message to bot to authorize yourself.  
At this point you are done and will receive alerts via Telegram bot in case of either your node is offline or has missed a block