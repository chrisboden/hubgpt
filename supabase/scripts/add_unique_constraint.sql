-- Add unique constraint to path column
ALTER TABLE prompt_includes ADD CONSTRAINT prompt_includes_path_key UNIQUE (path); 