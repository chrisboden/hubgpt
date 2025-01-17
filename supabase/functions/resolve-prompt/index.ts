import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  // Handle CORS
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // Create Supabase client
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_ANON_KEY') ?? ''
    )

    // Get advisor name from request
    const { advisor_name } = await req.json()
    if (!advisor_name) {
      throw new Error('advisor_name is required')
    }

    // Get advisor from database
    const { data: advisor, error: advisorError } = await supabaseClient
      .from('advisors')
      .select('*')
      .eq('name', advisor_name)
      .single()

    if (advisorError || !advisor) {
      throw new Error(`Advisor not found: ${advisorError?.message}`)
    }

    // Find all includes in the system message
    const includePattern = /<\$([^$]+)\$>/g
    const includes = [...advisor.system_message.matchAll(includePattern)]
      .map(match => match[1])

    // Fetch all includes in parallel
    const includeContents = await Promise.all(
      includes.map(async (path) => {
        const { data, error } = await supabaseClient
          .storage
          .from('includes')
          .download(path)

        if (error) {
          console.error(`Error fetching include ${path}: ${error.message}`)
          return { path, content: `[Include ${path} not found]` }
        }

        const content = await data.text()
        return { path, content }
      })
    )

    // Replace all includes in the system message
    let resolvedMessage = advisor.system_message
    includeContents.forEach(({ path, content }) => {
      resolvedMessage = resolvedMessage.replace(`<$${path}$>`, content)
    })

    // Return resolved advisor
    const response = {
      ...advisor,
      system_message: resolvedMessage
    }

    return new Response(
      JSON.stringify(response),
      { 
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json',
          'Cache-Control': 'public, max-age=60'
        }
      }
    )

  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      { 
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  }
}) 