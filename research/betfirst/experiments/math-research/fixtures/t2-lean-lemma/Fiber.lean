import Mathlib

/-- If every fiber of `f` over `T` has at most `c` points of `S`, and `f` maps `S` into `T`,
then `S` has at most `T.card * c` points. -/
theorem fiber_bound {α β : Type*} [DecidableEq β] (S : Finset α) (f : α → β) (T : Finset β)
    (hT : ∀ a ∈ S, f a ∈ T) (c : ℝ)
    (hk : ∀ b ∈ T, ((S.filter fun a => f a = b).card : ℝ) ≤ c) :
    (S.card : ℝ) ≤ T.card * c := by
  sorry
