import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  "https://sqjrspgoaqueaxxmhxvu.supabase.co",
  "sb_publishable_x_SdXKNvrsO0uHiCrQhwKA_CWMD2MRr"
);

export default supabase;