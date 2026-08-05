const axios = require('axios');
const fs = require('fs');
const FormData = require('form-data');
const path = require('path');

async function run() {
  try {
    // 1. Login
    const loginRes = await axios.post('http://localhost:8000/api/v1/auth/login', {
      email: 'chinmoy@example.com',
      password: 'chinmoy123'
    });
    const token = loginRes.data.data.access_token;
    console.log('Got token:', token);

    // 2. Upload
    const filePath = path.join(__dirname, '../dummy_contract.txt');
    const form = new FormData();
    form.append('document_type', 'other');
    form.append('file', fs.createReadStream(filePath));

    console.log('Sending upload request...');
    const uploadRes = await axios.post('http://localhost:8000/api/v1/documents/upload', form, {
      headers: {
        'Authorization': `Bearer ${token}`,
        ...form.getHeaders()
      }
    });

    console.log('Upload response:', uploadRes.status, uploadRes.data);
  } catch (err) {
    if (err.response) {
      console.error('Error response:', err.response.status, err.response.data);
    } else {
      console.error('Network/Error:', err.message);
    }
  }
}

run();
