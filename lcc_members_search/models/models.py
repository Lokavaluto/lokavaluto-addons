from odoo import models, fields, api


class lcc_members_search(models.Model):
    _name = "lcc_members_search.lcc_members_search"
    _description = "lcc_members_search.lcc_members_search"

    name = fields.Char()
    value = fields.Integer()


#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
