{
  description = "NixOS configuration for multiple machines using flakes";

  nixConfig = {
    experimental-features = [ "nix-command" "flakes" ];
  };

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    nixpkgs-stable.url = "github:nixos/nixpkgs/nixos-25.05";
    home-manager.url = "github:nix-community/home-manager/release-25.05";
    home-manager.inputs.nixpkgs.follows = "nixpkgs";
    plasma-manager.url = "github:pjones/plasma-manager";
    plasma-manager.inputs.nixpkgs.follows = "nixpkgs";
    sops-nix.url = "github:Mic92/sops-nix";
    sops-nix.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, nixpkgs-stable, home-manager, plasma-manager, sops-nix }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      pkgs-stable = nixpkgs-stable.legacyPackages.${system};
    in
    {
      nixosConfigurations = {
        # Laptop machine configuration
        brian-laptop = nixpkgs.lib.nixosSystem {
          inherit system;
          modules = [
            ./machines/brian-laptop/configuration.nix
            ./machines/brian-laptop/hardware-configuration.nix
            home-manager.nixosModules.home-manager
            {
              home-manager.useGlobalPkgs = true;
              home-manager.useUserPackages = true;
              home-manager.backupFileExtension = "backup";
              home-manager.users.brian = import ./machines/brian-laptop/home.nix;
              # Make plasma-manager available (renamed: homeManagerModules -> homeModules; attr is plasma-manager)
              home-manager.sharedModules = [ plasma-manager.homeModules.plasma-manager ];
            }
          ];
        };

        # Server machine configuration
        superheavy = nixpkgs-stable.lib.nixosSystem {
          inherit system;
          modules = [
            ./machines/superheavy/configuration.nix
            ./machines/superheavy/hardware-configuration.nix
            sops-nix.nixosModules.sops
          ];
        };

        # Server machine configuration
        docker = nixpkgs-stable.lib.nixosSystem {
          inherit system;
          modules = [
            ./machines/docker/configuration.nix
            ./machines/docker/hardware-configuration.nix
          ];
        };

        # Server machine configuration
        backup = nixpkgs-stable.lib.nixosSystem {
          inherit system;
          modules = [
            ./machines/backup/configuration.nix
            ./machines/backup/hardware-configuration.nix
          ];
        };
      };

      # Development shells
      devShells.${system} = {
        # Default shell for working with this flake
        default = pkgs.mkShell {
          buildInputs = with pkgs; [
            nixfmt
            nix-output-monitor
            sops
            age
          ];
        };

        # Python 3.13 development shell
        python = pkgs.mkShell {
          buildInputs = with pkgs; [
            python313
            python313Packages.pip
            python313Packages.setuptools
            python313Packages.wheel
            python313Packages.virtualenv
            python313Packages.black
            python313Packages.pytest
            python313Packages.ipython

            #Skylight dependencies
            python313Packages.django
            python313Packages.pillow
            python313Packages.requests
            python313Packages.beautifulsoup4
            python313Packages.google-api-python-client
            python313Packages.google-auth
            python313Packages.google-auth-httplib2
            python313Packages.google-auth-oauthlib
          ];
        };
      };
    };
}