import { createContext, useContext, useState, type ReactNode } from 'react';

export type CertificateType = 
  | "Egyptian Thanaweya Amma (Science)"
  | "Egyptian Thanaweya Amma (Math)"
  | "Egyptian Thanaweya Amma (Literature)"
  | "IGCSE"
  | "American Diploma"
  | "Other";

export type StudentGroup = "supportive_states" | "other_states";

export interface StudentProfile {
  certificate_type: CertificateType | "";
  high_school_percentage: number | null;
  student_group: StudentGroup;
  budget: number | null;
  preferred_branch: string | "";
  preferred_city: string | "";
  interests: string[];
  track_type: "regular" | "fast_track";
}

interface StudentContextType {
  profile: StudentProfile;
  updateProfile: (updates: Partial<StudentProfile>) => void;
}

const defaultProfile: StudentProfile = {
  certificate_type: "",
  high_school_percentage: null,
  student_group: "supportive_states",
  budget: null,
  preferred_branch: "",
  preferred_city: "",
  interests: [],
  track_type: "regular",
};

const StudentContext = createContext<StudentContextType | undefined>(undefined);

export function StudentProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<StudentProfile>(defaultProfile);

  const updateProfile = (updates: Partial<StudentProfile>) => {
    setProfile(prev => ({ ...prev, ...updates }));
  };

  return (
    <StudentContext.Provider value={{ profile, updateProfile }}>
      {children}
    </StudentContext.Provider>
  );
}

export function useStudent() {
  const context = useContext(StudentContext);
  if (context === undefined) {
    throw new Error("useStudent must be used within a StudentProvider");
  }
  return context;
}
