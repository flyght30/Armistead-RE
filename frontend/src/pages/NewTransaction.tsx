import React, { useState } from 'react';
import apiClient from '../lib/api';
import FileUpload from '../components/FileUpload';

const NewTransaction: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      setFile(event.target.files[0]);
    }
  };

  const handleSubmit = async () => {
    if (!file) return;

    setUploading(true);
    try {
      await apiClient.post('/transactions', { file });
      alert('Transaction created successfully');
    } catch (error) {
      console.error(error);
      alert('Error creating transaction');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <h1>New Transaction</h1>
      <FileUpload onChange={handleFileChange} />
      {file && <p>Selected file: {file.name}</p>}
      <button onClick={handleSubmit} disabled={uploading}>
        {uploading ? 'Uploading...' : 'Create Transaction'}
      </button>
    </div>
  );
};

export default NewTransaction;
