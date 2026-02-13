import React from 'react';
import { Party } from '../types/party';

const PartyCard: React.FC<{ party: Party }> = ({ party }) => {
  return (
    <div className="border p-4 mb-2">
      <h3>{party.name}</h3>
      <p>Role: {party.role}</p>
      <pre>Contact Info: {JSON.stringify(party.contact_info, null, 2)}</pre>
    </div>
  );
};

export default PartyCard;
