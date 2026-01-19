import type React from "react";
import StudioContainer from "./StudioContainer";
import type { StudioProps } from "./types";

interface StudioPageProps extends StudioProps {
  isAdmin?: boolean;
}

const StudioPage: React.FC<StudioPageProps> = ({ isAdmin = false, ...props }) => {
  // Simple admin check - in real app this would come from auth context
  if (!isAdmin) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-black font-mono text-white">
        <div className="text-center">
          <h1 className="mb-4 font-bold text-2xl text-pandora-cyan">STUDIO ACCESS RESTRICTED</h1>
          <p className="mb-8 text-gray-400">
            Studio is currently in beta and only accessible to administrators.
          </p>
          <div className="max-w-md rounded-lg border border-pandora-cyan/30 p-8">
            <div className="mb-4 flex items-center gap-3">
              <div className="h-2 w-2 animate-pulse rounded-full bg-red-500" />
              <span className="text-gray-300 text-sm">Status: BETA ACCESS ONLY</span>
            </div>
            <div className="space-y-1 text-gray-500 text-xs">
              <p>• Full access will be available when the beta phase is complete</p>
              <p>• Administrators can test all generation features</p>
              <p>• Regular users will get access soon</p>
            </div>
          </div>
          <div className="mt-8 text-gray-600 text-xs">
            <p>Need access? Contact your system administrator</p>
          </div>
        </div>
      </div>
    );
  }

  return <StudioContainer {...props} />;
};

export default StudioPage;
