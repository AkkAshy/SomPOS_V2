const dgram = require('dgram');
const server = dgram.createSocket('udp4');

const BROADCAST_ADDR = '255.255.255.255';
const PORT = 41234;
const MESSAGE = Buffer.from(JSON.stringify({
    type: 'SERVER_ANNOUNCE',
    port: 41234 // порт, на котором работает сервер
}));

server.bind(() => {
    server.setBroadcast(true);
    console.log('Broadcasting every 3 seconds...');
    setInterval(() => {
        server.send(MESSAGE, 0, MESSAGE.length, PORT, BROADCAST_ADDR, (err) => {
            if (err) console.error('Broadcast error:', err);
        });
    }, 3000);
});
