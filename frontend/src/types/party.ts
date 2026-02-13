import { z } from 'zod';

export const PartySchema = z.object({
  id: z.string(),
  name: z.string(),
  role: z.string(),
  contact_info: z.record(z.string()),
});

export type Party = z.infer<typeof PartySchema>;
