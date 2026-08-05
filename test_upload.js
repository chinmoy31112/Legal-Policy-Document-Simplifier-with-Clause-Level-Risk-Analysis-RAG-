const axios = require('axios');
const fs = require('fs');
const FormData = require('form-data');

async function testUpload() {
  const form = new FormData();
  form.append('file', fs.createReadStream('c:/Users/chinm/Downloads/Legal & Policy Document Simplifier with Clause-Level Risk Analysis (RAG)/dummy_contract.txt'));
  form.append('document_type', 'other');

  try {
    const res = await axios.post('http://localhost:8000/api/v1/documents/upload', form, {
      headers: form.getHeaders(),
    });
    console.log('Success:', res.data);
  } catch (err) {
    console.error('Error:', err.response ? err.response.data : err.message);
  }
}

testUpload();
