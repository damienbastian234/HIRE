import { useEffect, useState } from "react";
import Input from "../components/Input";
import Button from "../components/Button";
import ToastContainer from "../components/Toast";
import useToast from "../hooks/useToast";
import useAuth from "../hooks/useAuth";
import { getProfile, updateProfile } from "../services/api";

export default function ProfilePage() {
  const { updateSessionUser } = useAuth();
  const [form, setForm] = useState({
    name: "",
    title: "",
    email: "",
    location: "",
  });
  const [isSaving, setIsSaving] = useState(false);
  const { toasts, addToast, removeToast } = useToast();

  useEffect(() => {
    const loadProfile = async () => {
      try {
        const { data } = await getProfile();
        setForm((prev) => ({ ...prev, ...data }));
      } catch (error) {
        addToast(error.response?.data?.detail || "Unable to load profile.", "error");
      }
    };

    loadProfile();
  }, [addToast]);

  const handleSave = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      const { data } = await updateProfile(form);
      // Handle both response structures: { profile: {...} } and direct {...}
      const apiProfile = data.profile || data;
      const nextProfile = apiProfile || form;
      setForm((prev) => ({ ...prev, ...nextProfile }));
      
      // Ensure all necessary fields are included when updating session
      updateSessionUser({ 
        name: nextProfile.name,
        title: nextProfile.title,
        email: nextProfile.email,
        location: nextProfile.location,
        role: "candidate" 
      });
      
      addToast("Profile updated.", "success");
      
      // Refresh profile to get latest data
      const { data: profileResponse } = await getProfile();
      const refreshedProfile = profileResponse.profile || profileResponse;
      setForm((prev) => ({ ...prev, ...refreshedProfile }));
      
      // Update session with refreshed data
      updateSessionUser({ 
        name: refreshedProfile.name,
        title: refreshedProfile.title,
        email: refreshedProfile.email,
        location: refreshedProfile.location,
        role: "candidate" 
      });
    } catch (error) {
      addToast(error.response?.data?.detail || "Unable to update profile.", "error");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-xl">
      <div className="flex items-center gap-4">
        <span className="flex h-14 w-14 items-center justify-center rounded-full bg-ink font-display text-lg font-semibold text-signal">
          {form.name?.charAt(0) || "U"}
        </span>
        <div>
          <h1 className="text-xl font-semibold">{form.name}</h1>
          <p className="text-sm text-slate">{form.title}</p>
        </div>
      </div>

      <form onSubmit={handleSave} className="mt-8 flex flex-col gap-4">
        <Input label="Full name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <Input label="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        <Input
          label="Email"
          type="email"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
        />
        <Input label="Location" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
        <Button type="submit" variant="signal" size="lg" isLoading={isSaving} className="mt-2 self-start">
          Save changes
        </Button>
      </form>

      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </div>
  );
}
