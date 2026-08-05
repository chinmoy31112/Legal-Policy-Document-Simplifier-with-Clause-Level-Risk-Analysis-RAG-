const http = require('http');
const fs = require('fs');
const path = require('path');

const boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW';
const filePath = 'dummy_contract.txt';

if (!fs.existsSync(filePath)) {
  fs.writeFileSync(filePath, 'dummy content');
}

// 1. Login to get token
const loginData = JSON.stringify({
  email: "chinmoy@example.com",
  password: "chinmoy123"
});

const loginReq = http.request({
  hostname: 'localhost',
  port: 8000,
  path: '/api/v1/auth/login',
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(loginData)
  }
}, (res) => {
  let loginResData = '';
  res.on('data', chunk => loginResData += chunk);
  res.on('end', () => {
    const token = JSON.parse(loginResData).data.access_token;
    
    // 2. Upload
    let postData = '';
    postData += '--' + boundary + '\r\n';
    postData += 'Content-Disposition: form-data; name="document_type"\r\n\r\nother\r\n';
    postData += '--' + boundary + '\r\n';
    postData += 'Content-Disposition: form-data; name="file"; filename="dummy_contract.txt"\r\n';
    postData += 'Content-Type: text/plain\r\n\r\n';
    postData += fs.readFileSync(filePath, 'utf8') + '\r\n';
    postData += '--' + boundary + '--\r\n';

    const req = http.request({
      hostname: 'localhost',
      port: 8000,
      path: '/api/v1/documents/upload',
      method: 'POST',
      headers: {
        'Content-Type': 'multipart/form-data; boundary=' + boundary,
        'Content-Length': Buffer.byteLength(postData),
        'Authorization': 'Bearer ' + token
      }
    }, (uploadRes) => {
      let uploadData = '';
      uploadRes.on('data', chunk => uploadData += chunk);
      uploadRes.on('end', () => console.log('Response:', uploadRes.statusCode, uploadData));
    });

    req.write(postData);
    req.end();
  });
});
loginReq.write(loginData);
loginReq.end();
