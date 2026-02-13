import React, { useState } from 'react';
import { useDropzone } from 'react-dropzone';

const FileUpload: React.FC<{ onChange: (file: File) => void }> = ({ onChange }) => {
  const [files, setFiles] = useState<File[]>([]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles(acceptedFiles);
    onChange(acceptedFiles[0]);
  }, [onChange]);

  const {getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop });

  return (
    <div {...getRootProps()} className="border-dashed border-2 p-4">
      <input {...getInputProps()} />
      {
        isDragActive ?
          <p>Drop the files here ...</p> :
          <p>Drag 'n' drop some files here, or click to select files</p>
      }
    </div>
  );
};

export default FileUpload;
