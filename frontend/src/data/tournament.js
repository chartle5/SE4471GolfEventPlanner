export const tournamentState = {
  id: '',
  name: '',
  date: '',
  venue: '',
  format: '',
  numberOfDays: 0,
  playerCount: 0,
  eventType: '',        // 'individual' | 'team'
  teamSize: 0,          // players per team (1 if individual, 2 or 4 if team)
  registrationDeadline: '',
  entryFee: 0,          // optional
  description: '',      // optional
  teeTimeStart: '08:00',
  teeTimeInterval: 12,
  teeGroupSize: 4,      // players per tee-time slot (2 or 4)
  sponsors: [],
  catering: '',
  budget: 0,
  cateringEnabled: false,
  cateringBudget: 0,
  cateringItems: '',
  cateringServingTime: '',
  cateringDietaryNotes: '',
  staffing: {
    volunteers: 0,
    staff: 0
  },
  accessibility: '',
  notes: '',
  constraints: []
}