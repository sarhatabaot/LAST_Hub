const fastify = require('fastify')({ logger: true });
const services = require('./services.json');

// Route for /hub
fastify.get('/hub/', async (request, reply) => {
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
      .card-link,
      .card-link:visited,
      .card-link:hover,
      .card-link:active {
        text-decoration: none;
        color: inherit;
      }

    </style>
  </head>
  <body>
    <main>
      <div class="grid">
  `;

  services.forEach(s => {
    html += `
      <div>
        <a href="${s.path}" class="card-link contrast">
          <article class="card">
            <img src="${s.icon}" alt="${s.name}">
            <h3>${s.name}</h3>
            <p>${s.description}</p>
          </article>
        </a>
      </div>
    `;
  });

  html += `</div></main></body></html>`;
  return reply.type('text/html').send(html);
});

// Start server
fastify.listen({ port: 8085, host: '0.0.0.0' }, (err, address) => {
  if (err) throw err;
  console.log(`Service hub running at ${address}/hub`);
});
