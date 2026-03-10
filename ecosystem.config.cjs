module.exports = {
  apps: [{
    name: 'Elliot',
    script: '/home/elliotbot/.npm-global/bin/openclaw',
    args: 'gateway run',
    cwd: '/home/elliotbot/clawd',
    node_args: '--dns-result-order=ipv4first',
    env: {
      NODE_ENV: 'production'
    },
    restart_delay: 3000,
    max_restarts: 5,
    autorestart: true
  }]
};
