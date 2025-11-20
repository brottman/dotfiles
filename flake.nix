{
  description = "NixOS configuration for multiple machines using flakes";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    home-manager = {
      url = "github:nix-community/home-manager/master";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, home-manager }:
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
              home-manager.users.user = import ./machines/brian-laptop/home.nix;
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

        # Docker machine configuration
        docker = nixpkgs.lib.nixosSystem {
          inherit system;
          modules = [
            ./machines/docker/configuration.nix
            ./machines/docker/hardware-configuration.nix
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
