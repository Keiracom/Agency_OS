module.exports = {
  apps: [{
    name: 'AgencyOS',
    script: '/home/elliotbot/.npm-global/bin/clawdbot',
    args: 'gateway run',
    cwd: '/home/elliotbot/clawd',
    node_args: '--dns-result-order=ipv4first',
    env: {
      NODE_ENV: 'production'
    },
    restart_delay: 3000,
    max_restarts: 10,
    autorestart: true
  }]
};
