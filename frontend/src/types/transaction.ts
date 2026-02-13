import { z } from 'zod';

export const TransactionSchema = z.object({
  id: z.string(),
  title: z.string(),
  status: z.string(),
  file_path: z.string(),
  created_by_id: z.string(),
});

export type Transaction = z.infer<typeof TransactionSchema>;
