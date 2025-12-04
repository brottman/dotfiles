{
  description = "NixOS configuration for multiple machines using flakes";

  nixConfig = {
    experimental-features = [ "nix-command" "flakes" ];
  };

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    nixpkgs-stable.url = "github:nixos/nixpkgs/nixos-25.11";
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
      
      # CodeNomad package - wrapper around npx for the npm package
      codenomad = pkgs.writeShellApplication {
        name = "codenomad";
        runtimeInputs = [ pkgs.nodejs ];
        text = ''
          exec ${pkgs.nodejs}/bin/npx --yes @neuralnomads/codenomad "$@"
        '';
        meta = with pkgs.lib; {
          description = "A fast, multi-instance workspace for running OpenCode sessions";
          homepage = "https://github.com/NeuralNomadsAI/CodeNomad";
          license = licenses.mit;
        };
      };
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
            {
              # Make CodeNomad available
              nixpkgs.overlays = [
                (final: prev: {
                  codenomad = codenomad;
                })
              ];
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
      };
    };
}