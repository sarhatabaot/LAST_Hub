const fastify = require('fastify')({ logger: true });
const config = require('./services.json');

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
      main { padding: 2rem; }
      .section { margin-bottom: 3rem; }
      .section h2 { margin-bottom: 1.5rem; text-transform: capitalize; }
      .grid { gap: 1rem; }
      .card { text-align: center; }
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
  `;

  // Check if config has sections (observers, developers, etc.)
  const hasSections = !Array.isArray(config);
  
  if (hasSections) {
    // Render each section with its services
    Object.entries(config).forEach(([sectionName, services]) => {
      html += `
      <div class="section">
        <h2>${sectionName}</h2>
        <div class="grid">
      `;
      services.forEach(s => {
        html += `
        <div>
          <a href="${s.path}" class="card-link contrast">
            <article class="card">
              ${s.icon ? `<img src="${s.icon}" alt="${s.name}">` : ''}
              <h3>${s.name}</h3>
              <p>${s.description}</p>
            </article>
          </a>
        </div>
        `;
      });
      html += `</div></div>`;
    });
  } else {
    // Fallback: render as a single flat list (backwards compatible)
    html += `<div class="grid">`;
    config.forEach(s => {
      html += `
      <div>
        <a href="${s.path}" class="card-link contrast">
          <article class="card">
            ${s.icon ? `<img src="${s.icon}" alt="${s.name}">` : ''}
            <h3>${s.name}</h3>
            <p>${s.description}</p>
          </article>
        </a>
      </div>
      `;
    });
    html += `</div>`;
  }

  html += `</main></body></html>`;
  return reply.type('text/html').send(html);
});

// Start server
fastify.listen({ port: 8085, host: '0.0.0.0' }, (err, address) => {
  if (err) throw err;
  console.log(`Service hub running at ${address}/hub`);
});