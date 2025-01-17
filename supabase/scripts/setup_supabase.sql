-- Enable the necessary extensions
create extension if not exists "uuid-ossp";

-- Create the advisors table
create table if not exists public.advisors (
    id uuid default uuid_generate_v4() primary key,
    name text not null,
    model text,
    temperature float,
    max_tokens integer,
    tool_choice text,
    top_p float,
    frequency_penalty float,
    presence_penalty float,
    stream boolean,
    system_prompt text,
    created_at timestamp with time zone default timezone('utc'::text, now()),
    updated_at timestamp with time zone default timezone('utc'::text, now())
);

-- Create indexes
create index if not exists advisors_name_idx on public.advisors using btree (name);

-- Set up Row Level Security (RLS)
alter table public.advisors enable row level security;

-- Create policies
create policy "Enable read access for all users" on public.advisors
    for select
    to authenticated, anon
    using (true);

create policy "Enable insert for authenticated users only" on public.advisors
    for insert
    to authenticated
    with check (true);

create policy "Enable update for authenticated users only" on public.advisors
    for update
    to authenticated
    using (true)
    with check (true);

create policy "Enable delete for authenticated users only" on public.advisors
    for delete
    to authenticated
    using (true);

-- Grant necessary permissions
grant usage on schema public to anon, authenticated;
grant all on public.advisors to authenticated;
grant select on public.advisors to anon;
grant usage on sequence public.advisors_id_seq to anon, authenticated; 