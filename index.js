const fastify = require('fastify')({ logger: true });

// List of services
const services = [
  { name: 'Zorg', path: '/', description: 'Internal services', icon: 'https://img.icons8.com/color/96/000000/server.png' },
  { name: 'Grafana', path: '/grafana/', description: 'Monitoring dashboards', icon: 'https://img.icons8.com/color/96/000000/grafana.png' },
  { name: 'Grafana New', path: '/grafana-new/', description: 'New dashboards', icon: 'https://img.icons8.com/color/96/000000/grafana.png' },
  { name: 'Prometheus', path: '/prometheus/', description: 'Metrics collection', icon: 'https://raw.githubusercontent.com/prometheus/prometheus/main/documentation/images/prometheus-logo.svg'},
  { name: 'Sky Cam', path: '/sky-cam/', description: 'Live camera feed', icon: 'https://img.icons8.com/color/96/000000/camera.png' },
  { name: 'Observatory API', path: '/observatory-safety-api/', description: 'Sensor data & endpoints', icon: 'https://img.icons8.com/color/96/000000/api.png' },
];

// Route for /hub
fastify.get('/hub', async (request, reply) => {
  let html = `
  <!DOCTYPE html>
  <html lang="en">
  <head>
    <meta charset="UTF-8">
    <title>Our Services</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
    <style>
      main { display: flex; flex-wrap: wrap; justify-content: center; gap: 1rem; padding: 2rem; }
      .card { width: 200px; text-align: center; }
      .card img { width: 50px; height: 50px; margin-bottom: 0.5rem; }
    </style>
  </head>
  <body>
    <main>
  `;

  services.forEach(s => {
    html += `
      <article class="card">
        <img src="${s.icon}" alt="${s.name}">
        <h3>${s.name}</h3>
        <p>${s.description}</p>
        <a href="${s.path}" class="contrast">Open</a>
      </article>
    `;
  });

  html += `</main></body></html>`;
  return reply.type('text/html').send(html);
});

// Start server
fastify.listen({ port: 8085, host: '0.0.0.0' }, (err, address) => {
  if (err) throw err;
  console.log(`Service hub running at ${address}/hub`);
});
