from __future__ import print_function

import numpy as np
import matplotlib.pyplot as plt

import compressible.eos as eos
import mesh.patch as patch
import mesh.integration as integration
import compressible
import compressible_rk.fluxes as flx
from util import profile


class Simulation(compressible.Simulation):

    def substep(self, myd):
        """
        take a single substep in the RK timestepping starting with the 
        conservative state defined as part of myd
        """

        myg = myd.grid
        grav = self.rp.get_param("compressible.grav")

        # compute the source terms
        dens = myd.get_var("density")
        ymom = myd.get_var("y-momentum")
        ener = myd.get_var("energy")

        ymom_src = myg.scratch_array()
        ymom_src.v()[:,:] = dens.v()[:,:]*grav

        E_src = myg.scratch_array()
        E_src.v()[:,:] = ymom.v()[:,:]*grav

        k = myg.scratch_array(nvar=self.vars.nvar)

        flux_x, flux_y = flx.fluxes(myd, self.rp,
                                    self.vars, self.solid, self.tc)

        for n in range(self.vars.nvar):
            k.v(n=n)[:,:] = \
               (flux_x.v(n=n) - flux_x.ip(1, n=n))/myg.dx + \
               (flux_y.v(n=n) - flux_y.jp(1, n=n))/myg.dy

        k.v(n=self.vars.iymom)[:,:] += ymom_src.v()[:,:]
        k.v(n=self.vars.iener)[:,:] += E_src.v()[:,:]

        return k


    def evolve(self):
        """
        Evolve the equations of compressible hydrodynamics through a
        timestep dt.
        """

        tm_evolve = self.tc.timer("evolve")
        tm_evolve.begin()

        myg = self.cc_data.grid

        myd = self.cc_data

        order = self.rp.get_param("compressible.temporal_order")

        rk = integration.RKIntegrator(myd.t, self.dt, order=order)
        rk.set_start(myd)

        for s in range(order):
            ytmp = rk.get_stage_start(s)
            ytmp.fill_BC_all()
            k = self.substep(ytmp)
            rk.store_increment(s, k)

        rk.compute_final_update()


        # increment the time
        myd.t += self.dt
        self.n += 1

        tm_evolve.end()