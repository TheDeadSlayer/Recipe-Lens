// API type definitions — mirroring backend FastAPI schemas exactly.
// Keep in sync with:
//   backend/app/schemas/job.py  (JobRead)
//   backend/app/schemas/recipe.py (RecipeRead, Ingredient)

export type JobStatus =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'not_recipe'
  | 'failed'

export interface Job {
  id: string
  source_url: string
  status: JobStatus
  recipe_id: string | null
  error_message: string | null
  classification_reason: string | null
  created_at: string
  updated_at: string
}

export interface Ingredient {
  name: string
  quantity: string
}

export interface Recipe {
  id: string
  job_id: string
  source_url: string
  source_video_id: string | null
  title: string
  description: string | null
  ingredients: Ingredient[]
  equipment: string[]
  steps: string[]
  calories: number | null
  protein_g: number | null
  carbs_g: number | null
  fat_g: number | null
  created_at: string
}

export interface JobCreateResponse {
  already_exists: boolean
  job_id: string | null
  recipe_id: string | null
  recipe: Recipe | null
}
