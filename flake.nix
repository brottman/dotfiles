{
  description = "NixOS configuration for multiple machines using flakes";

  nixConfig = {
    experimental-features = [ "nix-command" "flakes" ];
  };

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    home-manager.url = "github:nix-community/home-manager";
    home-manager.inputs.nixpkgs.follows = "nixpkgs";
    plasma-manager.url = "github:pjones/plasma-manager";
    plasma-manager.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, home-manager, plasma-manager }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
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
        superheavy = nixpkgs.lib.nixosSystem {
          inherit system;
          modules = [
            ./machines/superheavy/configuration.nix
            ./machines/superheavy/hardware-configuration.nix
          ];
        };

        # Server machine configuration
        docker = nixpkgs.lib.nixosSystem {
          inherit system;
          modules = [
            ./machines/docker/configuration.nix
            ./machines/docker/hardware-configuration.nix
          ];
        };

        # Server machine configuration
        backup = nixpkgs.lib.nixosSystem {
          inherit system;
          modules = [
            ./machines/backup/configuration.nix
            ./machines/backup/hardware-configuration.nix
          ];
        };
      };

      # Development shell for working with this flake
      devShells.${system}.default = pkgs.mkShell {
        buildInputs = with pkgs; [
          nixfmt
          nix-output-monitor
        ];
      };
    };
}
