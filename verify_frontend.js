const http = require('http');

console.log('Testing Frontend Rendering...\n');

const options = {
  hostname: 'localhost',
  port: 5174,
  path: '/',
  method: 'GET',
  headers: {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
  }
};

const req = http.request(options, (res) => {
  let data = '';

  res.on('data', (chunk) => {
    data += chunk;
  });

  res.on('end', () => {
    console.log('✅ HTTP Status:', res.statusCode);
    console.log('✅ Content-Type:', res.headers['content-type']);
    console.log('✅ Content-Length:', res.headers['content-length'], 'bytes\n');

    const checks = {
      'React root div': data.includes('id="root"'),
      'Main script': data.includes('src="/src/main.tsx"'),
      'Vite client': data.includes('/@vite/client'),
      'Valid HTML doctype': data.includes('<!doctype html>'),
      'Meta viewport': data.includes('viewport'),
    };

    console.log('HTML Structure Checks:');
    Object.entries(checks).forEach(([check, passed]) => {
      console.log(`  ${passed ? '✅' : '❌'} ${check}`);
    });

    const allPass = Object.values(checks).every(v => v);
    console.log(`\n${allPass ? '✅ Frontend is properly configured!' : '❌ Some checks failed'}`);
    console.log('\nNext: Clear browser cache and hard refresh http://localhost:5174/');
    process.exit(0);
  });
});

req.on('error', (e) => {
  console.error('❌ Connection failed:', e.message);
  console.log('\nMake sure:');
  console.log('1. npm run dev is running');
  console.log('2. You are in the frontend directory');
  console.log('3. Port 5174 is not blocked');
  process.exit(1);
});

req.end();
