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
      <div className="min-h-screen bg-black text-white flex items-center justify-center font-mono">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-pandora-cyan mb-4">STUDIO ACCESS RESTRICTED</h1>
          <p className="text-gray-400 mb-8">
            Studio is currently in beta and only accessible to administrators.
          </p>
          <div className="border border-pandora-cyan/30 rounded-lg p-8 max-w-md">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
              <span className="text-sm text-gray-300">Status: BETA ACCESS ONLY</span>
            </div>
            <div className="text-xs text-gray-500 space-y-1">
              <p>• Full access will be available when the beta phase is complete</p>
              <p>• Administrators can test all generation features</p>
              <p>• Regular users will get access soon</p>
            </div>
          </div>
          <div className="text-xs text-gray-600 mt-8">
            <p>Need access? Contact your system administrator</p>
          </div>
        </div>
      </div>
    );
  }

  return <StudioContainer {...props} />;
};

export default StudioPage;
